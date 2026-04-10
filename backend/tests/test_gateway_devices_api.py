# ruff: noqa: S101
"""Integration tests for gateway device pairing API endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import require_org_admin
from app.api.gateway_devices import router as gateway_devices_router
from app.db.session import get_session
from app.models.gateway_devices import GatewayDevice
from app.models.gateways import Gateway
from app.models.organization_members import OrganizationMember
from app.models.organizations import Organization
from app.models.users import User
from app.services.organizations import OrganizationContext


async def _make_engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    return engine


def _build_test_app(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    org: Organization,
    member: OrganizationMember,
) -> FastAPI:
    app = FastAPI()
    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(gateway_devices_router)
    app.include_router(api_v1)

    async def _override_get_session() -> AsyncSession:
        async with session_maker() as session:
            yield session

    async def _override_require_org_admin() -> OrganizationContext:
        return OrganizationContext(organization=org, member=member)

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[require_org_admin] = _override_require_org_admin
    return app


async def _seed_org_and_gateway(
    session: AsyncSession,
) -> tuple[Organization, OrganizationMember, Gateway]:
    org_id = uuid4()
    user_id = uuid4()
    gateway_id = uuid4()

    org = Organization(id=org_id, name=f"org-{org_id}")
    session.add(org)
    user = User(
        id=user_id,
        clerk_user_id=f"clerk_{user_id.hex}",
        email=f"user-{user_id}@example.com",
        name="Test User",
    )
    session.add(user)
    member = OrganizationMember(
        id=uuid4(),
        organization_id=org_id,
        user_id=user_id,
        role="admin",
    )
    session.add(member)
    gateway = Gateway(
        id=gateway_id,
        organization_id=org_id,
        name="Test Gateway",
        url="ws://gateway.example:18789/ws",
        workspace_root="/tmp/workspace",
    )
    session.add(gateway)
    await session.commit()
    return org, member, gateway


@pytest.mark.asyncio
async def test_register_and_list_device() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # Register a device
            response = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123deadbeef",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                    "name": "laptop-dev",
                },
            )
            assert response.status_code == 201
            body = response.json()
            assert body["device_id"] == "abc123deadbeef"
            assert body["name"] == "laptop-dev"
            assert body["status"] == "pending"
            assert body["gateway_id"] == str(gateway.id)
            device_id = body["id"]

            # List devices
            list_response = await client.get(f"/api/v1/gateways/{gateway.id}/devices")
            assert list_response.status_code == 200
            items = list_response.json()["items"]
            assert len(items) == 1
            assert items[0]["id"] == device_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_devices_with_status_filter() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # Register two devices
            await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "device-pending",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            reg2 = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "device-to-approve",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device2_id = reg2.json()["id"]

            # Approve device2
            await client.patch(
                f"/api/v1/gateways/{gateway.id}/devices/{device2_id}",
                json={"status": "approved"},
            )

            # Filter by pending
            pending = await client.get(
                f"/api/v1/gateways/{gateway.id}/devices",
                params={"status_filter": "pending"},
            )
            assert pending.status_code == 200
            assert len(pending.json()["items"]) == 1
            assert pending.json()["items"][0]["device_id"] == "device-pending"

            # Filter by approved
            approved = await client.get(
                f"/api/v1/gateways/{gateway.id}/devices",
                params={"status_filter": "approved"},
            )
            assert approved.status_code == 200
            assert len(approved.json()["items"]) == 1
            assert approved.json()["items"][0]["device_id"] == "device-to-approve"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_single_device() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device_id = reg.json()["id"]

            get_response = await client.get(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}"
            )
            assert get_response.status_code == 200
            assert get_response.json()["id"] == device_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_approve_device_sets_approved_at() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device_id = reg.json()["id"]

            patch = await client.patch(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}",
                json={"status": "approved"},
            )
            assert patch.status_code == 200
            body = patch.json()
            assert body["status"] == "approved"
            assert body["approved_at"] is not None
            assert body["revoked_at"] is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_device_sets_revoked_at() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device_id = reg.json()["id"]

            patch = await client.patch(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}",
                json={"status": "revoked"},
            )
            assert patch.status_code == 200
            body = patch.json()
            assert body["status"] == "revoked"
            assert body["revoked_at"] is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rename_device() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                    "name": "old-name",
                },
            )
            device_id = reg.json()["id"]

            patch = await client.patch(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}",
                json={"name": "new-name"},
            )
            assert patch.status_code == 200
            assert patch.json()["name"] == "new-name"
            assert patch.json()["status"] == "pending"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delete_device() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device_id = reg.json()["id"]

            delete = await client.delete(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}"
            )
            assert delete.status_code == 200
            assert delete.json() == {"ok": True}

            # Verify it's gone
            get_response = await client.get(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}"
            )
            assert get_response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_device_returns_404_for_wrong_gateway() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device_id = reg.json()["id"]

            wrong_gateway_id = uuid4()
            get_response = await client.get(
                f"/api/v1/gateways/{wrong_gateway_id}/devices/{device_id}"
            )
            assert get_response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_status_transition_returns_422() -> None:
    engine = await _make_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        org, member, gateway = await _seed_org_and_gateway(session)

    app = _build_test_app(session_maker, org=org, member=member)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            reg = await client.post(
                f"/api/v1/gateways/{gateway.id}/devices",
                json={
                    "device_id": "abc123",
                    "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMFIwEA==\n-----END PUBLIC KEY-----",
                },
            )
            device_id = reg.json()["id"]

            patch = await client.patch(
                f"/api/v1/gateways/{gateway.id}/devices/{device_id}",
                json={"status": "bogus-status"},
            )
            assert patch.status_code == 422
    finally:
        await engine.dispose()

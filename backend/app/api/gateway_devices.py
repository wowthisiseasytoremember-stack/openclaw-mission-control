"""CRUD endpoints for gateway device pairing identity and approval lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import col

from app.api.deps import require_org_admin
from app.core.auth import AuthContext, get_auth_context
from app.core.time import utcnow
from app.db import crud
from app.db.pagination import paginate
from app.db.session import get_session
from app.models.gateway_devices import GatewayDevice
from app.schemas.common import OkResponse
from app.schemas.gateway_devices import (
    DEVICE_STATUSES,
    GatewayDeviceCreate,
    GatewayDeviceRead,
    GatewayDeviceUpdate,
)
from app.schemas.pagination import DefaultLimitOffsetPage
from app.services.openclaw.admin_service import GatewayAdminLifecycleService

if TYPE_CHECKING:
    from fastapi_pagination.limit_offset import LimitOffsetPage
    from sqlmodel.ext.asyncio.session import AsyncSession

    from app.services.organizations import OrganizationContext

router = APIRouter(prefix="/gateways", tags=["gateways"])
SESSION_DEP = Depends(get_session)
AUTH_DEP = Depends(get_auth_context)
ORG_ADMIN_DEP = Depends(require_org_admin)
STATUS_QUERY = Query(default=None)

_RUNTIME_TYPE_REFERENCES = (UUID,)


async def _require_device(
    gateway_id: UUID,
    device_id: UUID,
    session: AsyncSession,
    organization_id: UUID,
) -> GatewayDevice:
    """Load a device belonging to a gateway in the caller's org, or raise 404."""
    service = GatewayAdminLifecycleService(session)
    await service.require_gateway(
        gateway_id=gateway_id,
        organization_id=organization_id,
    )
    device = await GatewayDevice.objects.by_id(device_id).first(session)
    if device is None or device.gateway_id != gateway_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return device


@router.get("/{gateway_id}/devices", response_model=DefaultLimitOffsetPage[GatewayDeviceRead])
async def list_gateway_devices(
    gateway_id: UUID,
    status_filter: str | None = STATUS_QUERY,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> LimitOffsetPage[GatewayDeviceRead]:
    """List devices registered against a gateway, optionally filtered by status."""
    service = GatewayAdminLifecycleService(session)
    await service.require_gateway(
        gateway_id=gateway_id,
        organization_id=ctx.organization.id,
    )

    query = GatewayDevice.objects.filter_by(gateway_id=gateway_id)
    if status_filter is not None:
        query = query.filter(col(GatewayDevice.status) == status_filter)

    statement = query.order_by(col(GatewayDevice.first_seen_at).desc()).statement
    return await paginate(session, statement)


@router.post(
    "/{gateway_id}/devices",
    response_model=GatewayDeviceRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_gateway_device(
    gateway_id: UUID,
    payload: GatewayDeviceCreate,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> GatewayDevice:
    """Register a new device identity against a gateway."""
    service = GatewayAdminLifecycleService(session)
    await service.require_gateway(
        gateway_id=gateway_id,
        organization_id=ctx.organization.id,
    )
    now = utcnow()
    device = await crud.create(
        session,
        GatewayDevice,
        gateway_id=gateway_id,
        device_id=payload.device_id,
        public_key_pem=payload.public_key_pem,
        name=payload.name,
        status="pending",
        first_seen_at=now,
        last_seen_at=now,
    )
    return device


@router.get("/{gateway_id}/devices/{device_id}", response_model=GatewayDeviceRead)
async def get_gateway_device(
    gateway_id: UUID,
    device_id: UUID,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> GatewayDevice:
    """Return one device by id for the given gateway."""
    return await _require_device(gateway_id, device_id, session, ctx.organization.id)


@router.patch("/{gateway_id}/devices/{device_id}", response_model=GatewayDeviceRead)
async def update_gateway_device(
    gateway_id: UUID,
    device_id: UUID,
    payload: GatewayDeviceUpdate,
    session: AsyncSession = SESSION_DEP,
    auth: AuthContext = AUTH_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> GatewayDevice:
    """Approve, revoke, or rename a device.

    Status transitions:
    - pending -> approved: sets approved_at and approved_by
    - pending/approved -> revoked: sets revoked_at
    """
    device = await _require_device(gateway_id, device_id, session, ctx.organization.id)
    updates = payload.model_dump(exclude_unset=True)

    new_status = updates.get("status")
    if new_status is not None and new_status not in DEVICE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{new_status}'. Must be one of: {sorted(DEVICE_STATUSES)}",
        )

    if new_status == "approved" and device.status != "approved":
        updates["approved_at"] = utcnow()
        updates["approved_by"] = auth.user.id if auth.user else None
        updates["revoked_at"] = None

    if new_status == "revoked" and device.status != "revoked":
        updates["revoked_at"] = utcnow()

    await crud.patch(session, device, updates)
    return device


@router.delete("/{gateway_id}/devices/{device_id}", response_model=OkResponse)
async def delete_gateway_device(
    gateway_id: UUID,
    device_id: UUID,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> OkResponse:
    """Hard-delete a device record from the gateway."""
    device = await _require_device(gateway_id, device_id, session, ctx.organization.id)
    await session.delete(device)
    await session.commit()
    return OkResponse()

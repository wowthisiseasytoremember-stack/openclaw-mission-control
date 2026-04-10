"""Schemas for gateway device pairing CRUD and status-change API payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

RUNTIME_ANNOTATION_TYPES = (datetime, UUID)

DEVICE_STATUSES = {"pending", "approved", "revoked"}


class GatewayDeviceCreate(SQLModel):
    """Payload for registering a new device against a gateway."""

    device_id: str
    public_key_pem: str
    name: str | None = None


class GatewayDeviceUpdate(SQLModel):
    """Payload for partial device updates — approve, revoke, or rename."""

    status: str | None = None
    name: str | None = None


class GatewayDeviceRead(SQLModel):
    """Device payload returned from read endpoints."""

    id: UUID
    gateway_id: UUID
    device_id: str
    public_key_pem: str
    name: str | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    approved_at: datetime | None = None
    approved_by: UUID | None = None
    revoked_at: datetime | None = None


class GatewayDeviceListParams(SQLModel):
    """Query parameters for listing devices with optional status filter."""

    status: str | None = Field(default=None)

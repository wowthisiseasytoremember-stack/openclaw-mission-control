"""GatewayDevice model representing device identities that connect to a gateway."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

RUNTIME_ANNOTATION_TYPES = (datetime,)


class GatewayDevice(QueryModel, table=True):
    """Device identity registered against a gateway with approval lifecycle state."""

    __tablename__ = "gateway_devices"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    gateway_id: UUID = Field(foreign_key="gateways.id", index=True)
    device_id: str = Field(index=True)
    public_key_pem: str
    name: str | None = Field(default=None)
    status: str = Field(default="pending", index=True)
    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    approved_at: datetime | None = Field(default=None)
    approved_by: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    revoked_at: datetime | None = Field(default=None)

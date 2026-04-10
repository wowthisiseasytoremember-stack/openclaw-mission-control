"""Board outbound webhook configuration model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

if TYPE_CHECKING:
    pass

RUNTIME_ANNOTATION_TYPES = (datetime,)


class BoardOutboundWebhook(QueryModel, table=True):
    """Outbound webhook configuration for delivering board events to external URLs."""

    __tablename__ = "board_outbound_webhooks"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    board_id: UUID = Field(foreign_key="boards.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    name: str
    target_url: str
    secret: str | None = Field(default=None)
    event_types: list[str] = Field(default_factory=list, sa_type=JSON)
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

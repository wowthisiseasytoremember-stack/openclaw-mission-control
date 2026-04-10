"""Schemas for board outbound webhook configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AnyHttpUrl, BeforeValidator, field_validator
from sqlmodel import SQLModel

from app.schemas.common import NonEmptyStr

RUNTIME_ANNOTATION_TYPES = (datetime, UUID, NonEmptyStr)

# Supported event type tokens — callers may pass any string; the model is
# deliberately open so new event types can be added without schema churn.
# This list is used only for documentation / hint purposes.
KNOWN_EVENT_TYPES = frozenset(
    {
        "task.created",
        "task.updated",
        "task.done",
        "task.deleted",
        "approval.pending",
        "approval.approved",
        "approval.rejected",
        "board.updated",
    }
)


def _normalize_secret(v: str | None) -> str | None:
    """Normalize blank/whitespace-only secrets to None."""
    if v is None:
        return None
    stripped = v.strip()
    return stripped or None


NormalizedSecret = Annotated[str | None, BeforeValidator(_normalize_secret)]


class BoardOutboundWebhookCreate(SQLModel):
    """Payload for creating a board outbound webhook."""

    name: NonEmptyStr
    target_url: AnyHttpUrl
    secret: NormalizedSecret = None
    event_types: list[str] = []
    enabled: bool = True

    @field_validator("event_types")
    @classmethod
    def _validate_event_types(cls, v: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in v:
            stripped = item.strip()
            if not stripped:
                raise ValueError("event_types entries must be non-empty strings.")
            normalized.append(stripped)
        return normalized


class BoardOutboundWebhookUpdate(SQLModel):
    """Payload for updating a board outbound webhook."""

    name: NonEmptyStr | None = None
    target_url: AnyHttpUrl | None = None
    secret: NormalizedSecret = None
    event_types: list[str] | None = None
    enabled: bool | None = None

    @field_validator("event_types")
    @classmethod
    def _validate_event_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        normalized: list[str] = []
        for item in v:
            stripped = item.strip()
            if not stripped:
                raise ValueError("event_types entries must be non-empty strings.")
            normalized.append(stripped)
        return normalized


class BoardOutboundWebhookRead(SQLModel):
    """Serialized board outbound webhook configuration."""

    id: UUID
    board_id: UUID
    organization_id: UUID
    name: str
    target_url: str
    has_secret: bool = False
    event_types: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class BoardOutboundWebhookTestResponse(SQLModel):
    """Response after sending a test event to an outbound webhook."""

    ok: bool
    status_code: int | None = None
    detail: str | None = None

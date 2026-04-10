"""Board outbound webhook configuration endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import col, select

from app.api.deps import get_board_for_user_read, get_board_for_user_write
from app.core.logging import get_logger
from app.core.time import utcnow
from app.db import crud
from app.db.pagination import paginate
from app.db.session import get_session
from app.models.board_outbound_webhooks import BoardOutboundWebhook
from app.schemas.board_outbound_webhooks import (
    BoardOutboundWebhookCreate,
    BoardOutboundWebhookRead,
    BoardOutboundWebhookTestResponse,
    BoardOutboundWebhookUpdate,
)
from app.schemas.common import OkResponse
from app.schemas.pagination import DefaultLimitOffsetPage
from app.services.outbound_webhooks.dispatch import dispatch_board_event

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination.limit_offset import LimitOffsetPage
    from sqlmodel.ext.asyncio.session import AsyncSession

    from app.models.boards import Board

router = APIRouter(
    prefix="/boards/{board_id}/outbound-webhooks",
    tags=["board-outbound-webhooks"],
)
SESSION_DEP = Depends(get_session)
BOARD_USER_READ_DEP = Depends(get_board_for_user_read)
BOARD_USER_WRITE_DEP = Depends(get_board_for_user_write)
logger = get_logger(__name__)


def _to_outbound_webhook_read(webhook: BoardOutboundWebhook) -> BoardOutboundWebhookRead:
    return BoardOutboundWebhookRead(
        id=webhook.id,
        board_id=webhook.board_id,
        organization_id=webhook.organization_id,
        name=webhook.name,
        target_url=webhook.target_url,
        has_secret=bool(webhook.secret),
        event_types=webhook.event_types,
        enabled=webhook.enabled,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


def _coerce_webhook_items(items: Sequence[object]) -> list[BoardOutboundWebhook]:
    values: list[BoardOutboundWebhook] = []
    for item in items:
        if not isinstance(item, BoardOutboundWebhook):
            msg = "Expected BoardOutboundWebhook items from paginated query"
            raise TypeError(msg)
        values.append(item)
    return values


async def _require_outbound_webhook(
    session: AsyncSession,
    *,
    board_id: UUID,
    webhook_id: UUID,
) -> BoardOutboundWebhook:
    webhook = (
        await session.exec(
            select(BoardOutboundWebhook)
            .where(col(BoardOutboundWebhook.id) == webhook_id)
            .where(col(BoardOutboundWebhook.board_id) == board_id),
        )
    ).first()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return webhook


@router.get("", response_model=DefaultLimitOffsetPage[BoardOutboundWebhookRead])
async def list_board_outbound_webhooks(
    board: Board = BOARD_USER_READ_DEP,
    session: AsyncSession = SESSION_DEP,
) -> LimitOffsetPage[BoardOutboundWebhookRead]:
    """List configured outbound webhooks for a board."""
    statement = (
        select(BoardOutboundWebhook)
        .where(col(BoardOutboundWebhook.board_id) == board.id)
        .order_by(col(BoardOutboundWebhook.created_at).desc())
    )

    def _transform(items: Sequence[object]) -> Sequence[object]:
        webhooks = _coerce_webhook_items(items)
        return [_to_outbound_webhook_read(value) for value in webhooks]

    return await paginate(session, statement, transformer=_transform)


@router.post("", response_model=BoardOutboundWebhookRead, status_code=status.HTTP_201_CREATED)
async def create_board_outbound_webhook(
    payload: BoardOutboundWebhookCreate,
    board: Board = BOARD_USER_WRITE_DEP,
    session: AsyncSession = SESSION_DEP,
) -> BoardOutboundWebhookRead:
    """Create a new outbound webhook for delivering board events to an external URL."""
    webhook = BoardOutboundWebhook(
        board_id=board.id,
        organization_id=board.organization_id,
        name=payload.name,
        target_url=str(payload.target_url),
        secret=payload.secret,
        event_types=payload.event_types,
        enabled=payload.enabled,
    )
    await crud.save(session, webhook)
    logger.info(
        "outbound_webhook.created",
        extra={
            "webhook_id": str(webhook.id),
            "board_id": str(board.id),
            "target_url": webhook.target_url,
        },
    )
    return _to_outbound_webhook_read(webhook)


@router.patch("/{webhook_id}", response_model=BoardOutboundWebhookRead)
async def update_board_outbound_webhook(
    webhook_id: UUID,
    payload: BoardOutboundWebhookUpdate,
    board: Board = BOARD_USER_WRITE_DEP,
    session: AsyncSession = SESSION_DEP,
) -> BoardOutboundWebhookRead:
    """Update an outbound webhook configuration."""
    webhook = await _require_outbound_webhook(
        session,
        board_id=board.id,
        webhook_id=webhook_id,
    )
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        # Coerce AnyHttpUrl to str if present
        if "target_url" in updates and updates["target_url"] is not None:
            updates["target_url"] = str(updates["target_url"])
        crud.apply_updates(webhook, updates)
        webhook.updated_at = utcnow()
        await crud.save(session, webhook)
    return _to_outbound_webhook_read(webhook)


@router.delete("/{webhook_id}", response_model=OkResponse)
async def delete_board_outbound_webhook(
    webhook_id: UUID,
    board: Board = BOARD_USER_WRITE_DEP,
    session: AsyncSession = SESSION_DEP,
) -> OkResponse:
    """Delete an outbound webhook configuration."""
    webhook = await _require_outbound_webhook(
        session,
        board_id=board.id,
        webhook_id=webhook_id,
    )
    await session.delete(webhook)
    await session.commit()
    logger.info(
        "outbound_webhook.deleted",
        extra={"webhook_id": str(webhook.id), "board_id": str(board.id)},
    )
    return OkResponse()


@router.post(
    "/{webhook_id}/test",
    response_model=BoardOutboundWebhookTestResponse,
    status_code=status.HTTP_200_OK,
)
async def test_board_outbound_webhook(
    webhook_id: UUID,
    board: Board = BOARD_USER_WRITE_DEP,
    session: AsyncSession = SESSION_DEP,
) -> BoardOutboundWebhookTestResponse:
    """Send a test event payload to the configured target URL and return the HTTP result."""
    webhook = await _require_outbound_webhook(
        session,
        board_id=board.id,
        webhook_id=webhook_id,
    )
    test_payload = {
        "event": "webhook.test",
        "board_id": str(board.id),
        "webhook_id": str(webhook.id),
        "message": "This is a test delivery from OpenClaw Mission Control.",
    }
    result = await dispatch_board_event(
        board_id=board.id,
        event_type="webhook.test",
        payload=test_payload,
        _override_webhook=webhook,
    )
    logger.info(
        "outbound_webhook.test",
        extra={
            "webhook_id": str(webhook.id),
            "board_id": str(board.id),
            "ok": result.ok,
            "status_code": result.status_code,
        },
    )
    return result

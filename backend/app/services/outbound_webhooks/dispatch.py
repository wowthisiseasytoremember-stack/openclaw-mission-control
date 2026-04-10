"""Outbound webhook dispatch service.

Delivers board events to externally-configured target URLs.  Supports
optional HMAC-SHA256 request signing and queued delivery with exponential
backoff retries.

Usage (fire-and-forget from a task/approval handler)::

    from app.services.outbound_webhooks.dispatch import dispatch_board_event

    await dispatch_board_event(
        board_id=board.id,
        event_type="task.created",
        payload={"task_id": str(task.id), "title": task.title},
    )

The dispatch function looks up all *enabled* outbound webhooks for the board
that subscribe to ``event_type`` (or have an empty ``event_types`` list,
which is treated as "subscribe to all events").  Each matching webhook is
delivered independently.

NOTE: This service is intentionally NOT wired into task/approval handlers
yet — that is the next integration step.  This module provides the callable
surface; wiring is deferred.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import httpx
from sqlmodel import col, select

from app.core.config import settings
from app.core.logging import get_logger
from app.core.time import utcnow
from app.models.board_outbound_webhooks import BoardOutboundWebhook
from app.services.queue import QueuedTask, enqueue_task_with_delay

if TYPE_CHECKING:
    from app.schemas.board_outbound_webhooks import BoardOutboundWebhookTestResponse

logger = get_logger(__name__)

OUTBOUND_TASK_TYPE = "outbound_webhook_delivery"
_OUTBOUND_QUEUE_NAME_SUFFIX = ":outbound"
_DEFAULT_TIMEOUT_SECONDS = 10.0
_SIGNATURE_HEADER = "X-OpenClaw-Signature-256"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _outbound_queue_name() -> str:
    return f"{settings.rq_queue_name}{_OUTBOUND_QUEUE_NAME_SUFFIX}"


def _sign_payload(secret: str, body: bytes) -> str:
    """Return ``sha256=<hex>`` HMAC signature for *body* using *secret*."""
    digest = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def _build_headers(webhook: BoardOutboundWebhook, body: bytes) -> dict[str, str]:
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "OpenClaw-MissionControl/1.0",
        "X-OpenClaw-Event": "outbound_webhook",
        "X-OpenClaw-Board-Id": str(webhook.board_id),
        "X-OpenClaw-Webhook-Id": str(webhook.id),
        "X-OpenClaw-Delivery-At": utcnow().isoformat(),
    }
    if webhook.secret:
        headers[_SIGNATURE_HEADER] = _sign_payload(webhook.secret, body)
    return headers


@dataclass
class DeliveryResult:
    """Outcome of a single outbound webhook delivery attempt."""

    ok: bool
    status_code: int | None = None
    detail: str | None = None


async def _deliver_once(
    webhook: BoardOutboundWebhook,
    event_type: str,
    payload: dict[str, Any],
) -> DeliveryResult:
    """POST *payload* to ``webhook.target_url``.  Returns a :class:`DeliveryResult`."""
    envelope: dict[str, Any] = {
        "event": event_type,
        "board_id": str(webhook.board_id),
        "webhook_id": str(webhook.id),
        "occurred_at": utcnow().isoformat(),
        "data": payload,
    }
    body = json.dumps(envelope, sort_keys=True).encode("utf-8")
    headers = _build_headers(webhook, body)

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post(
                webhook.target_url,
                content=body,
                headers=headers,
            )
        if response.is_success:
            return DeliveryResult(ok=True, status_code=response.status_code)
        logger.warning(
            "outbound_webhook.delivery.non_2xx",
            extra={
                "webhook_id": str(webhook.id),
                "board_id": str(webhook.board_id),
                "target_url": webhook.target_url,
                "event_type": event_type,
                "status_code": response.status_code,
            },
        )
        return DeliveryResult(
            ok=False,
            status_code=response.status_code,
            detail=f"Target returned HTTP {response.status_code}",
        )
    except httpx.TimeoutException as exc:
        logger.warning(
            "outbound_webhook.delivery.timeout",
            extra={
                "webhook_id": str(webhook.id),
                "board_id": str(webhook.board_id),
                "target_url": webhook.target_url,
                "error": str(exc),
            },
        )
        return DeliveryResult(ok=False, detail=f"Request timed out: {exc}")
    except Exception as exc:
        logger.exception(
            "outbound_webhook.delivery.error",
            extra={
                "webhook_id": str(webhook.id),
                "board_id": str(webhook.board_id),
                "target_url": webhook.target_url,
                "error": str(exc),
            },
        )
        return DeliveryResult(ok=False, detail=str(exc))


# ---------------------------------------------------------------------------
# Queue helpers for deferred / retried delivery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueuedOutboundDelivery:
    """Payload stored in the outbound delivery queue."""

    board_id: UUID
    webhook_id: UUID
    event_type: str
    payload: dict[str, Any]
    enqueued_at: datetime
    attempts: int = 0


def _task_from_outbound(delivery: QueuedOutboundDelivery) -> QueuedTask:
    return QueuedTask(
        task_type=OUTBOUND_TASK_TYPE,
        payload={
            "board_id": str(delivery.board_id),
            "webhook_id": str(delivery.webhook_id),
            "event_type": delivery.event_type,
            "payload": delivery.payload,
            "enqueued_at": delivery.enqueued_at.isoformat(),
            "attempts": delivery.attempts,
        },
        created_at=delivery.enqueued_at,
        attempts=delivery.attempts,
    )


def enqueue_outbound_delivery(delivery: QueuedOutboundDelivery, *, delay_seconds: float = 0) -> bool:
    """Push *delivery* onto the outbound webhook queue, optionally delayed."""
    try:
        task = _task_from_outbound(delivery)
        enqueue_task_with_delay(
            task,
            _outbound_queue_name(),
            delay_seconds=delay_seconds,
            redis_url=settings.rq_redis_url,
        )
        logger.info(
            "outbound_webhook.queue.enqueued",
            extra={
                "webhook_id": str(delivery.webhook_id),
                "board_id": str(delivery.board_id),
                "event_type": delivery.event_type,
                "attempt": delivery.attempts,
                "delay_seconds": delay_seconds,
            },
        )
        return True
    except Exception as exc:
        logger.warning(
            "outbound_webhook.queue.enqueue_failed",
            extra={
                "webhook_id": str(delivery.webhook_id),
                "board_id": str(delivery.board_id),
                "error": str(exc),
            },
        )
        return False


def _compute_retry_delay(attempts: int) -> float:
    base = float(settings.rq_dispatch_retry_base_seconds) * (2 ** max(0, attempts))
    return float(min(base, float(settings.rq_dispatch_retry_max_seconds)))


def _compute_retry_jitter(base_delay: float) -> float:
    upper_bound = float(
        min(float(settings.rq_dispatch_retry_max_seconds) / 10.0, float(base_delay) * 0.1)
    )
    return float(random.uniform(0.0, upper_bound))


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


async def dispatch_board_event(
    board_id: UUID,
    event_type: str,
    payload: dict[str, Any],
    *,
    _override_webhook: BoardOutboundWebhook | None = None,
) -> "BoardOutboundWebhookTestResponse":
    """Deliver *event_type* + *payload* to all matching enabled outbound webhooks.

    When ``_override_webhook`` is supplied (used by the test endpoint), only that
    single webhook is targeted regardless of its ``event_types`` subscription list.

    Returns a :class:`BoardOutboundWebhookTestResponse`-compatible result representing
    the last delivery attempt.  When dispatching to multiple webhooks the return value
    reflects the *last* webhook attempted; callers that need per-webhook results should
    call ``_deliver_once`` directly.
    """
    # Inline import to avoid circular import from the API layer.
    from app.schemas.board_outbound_webhooks import BoardOutboundWebhookTestResponse

    if _override_webhook is not None:
        webhooks: list[BoardOutboundWebhook] = [_override_webhook]
    else:
        # Resolve from DB — requires an async session.
        from app.db.session import async_session_maker

        async with async_session_maker() as session:
            stmt = (
                select(BoardOutboundWebhook)
                .where(col(BoardOutboundWebhook.board_id) == board_id)
                .where(col(BoardOutboundWebhook.enabled).is_(True))
            )
            rows = (await session.exec(stmt)).all()
            webhooks = [
                wh
                for wh in rows
                if not wh.event_types or event_type in wh.event_types
            ]

    if not webhooks:
        logger.debug(
            "outbound_webhook.dispatch.no_targets",
            extra={"board_id": str(board_id), "event_type": event_type},
        )
        return BoardOutboundWebhookTestResponse(
            ok=True,
            detail="No enabled outbound webhooks matched this event.",
        )

    last_result: DeliveryResult | None = None
    for webhook in webhooks:
        result = await _deliver_once(webhook, event_type, payload)
        last_result = result

        if not result.ok:
            # Enqueue for retry with exponential backoff
            delivery = QueuedOutboundDelivery(
                board_id=board_id,
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                enqueued_at=datetime.now(UTC),
                attempts=1,
            )
            delay = _compute_retry_delay(0)
            jitter = _compute_retry_jitter(delay)
            enqueue_outbound_delivery(delivery, delay_seconds=delay + jitter)

        logger.info(
            "outbound_webhook.dispatch.delivered",
            extra={
                "webhook_id": str(webhook.id),
                "board_id": str(board_id),
                "event_type": event_type,
                "ok": result.ok,
                "status_code": result.status_code,
            },
        )

    assert last_result is not None  # webhooks is non-empty
    return BoardOutboundWebhookTestResponse(
        ok=last_result.ok,
        status_code=last_result.status_code,
        detail=last_result.detail,
    )

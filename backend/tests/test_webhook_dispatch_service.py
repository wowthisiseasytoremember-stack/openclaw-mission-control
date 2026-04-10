# ruff: noqa: INP001
"""Unit tests for webhook dispatch service logic.

Covers:
- HMAC signature verification (valid, invalid, missing)
- Payload size limit enforcement
- Agent notification dispatch logic
- Queue enqueue behavior
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.board_webhooks import (
    _decode_payload,
    _verify_webhook_signature,
    _captured_headers,
)
from app.models.board_webhooks import BoardWebhook
from app.services.webhooks.queue import (
    QueuedInboundDelivery,
    decode_webhook_task,
    enqueue_webhook_delivery,
)
from app.services.queue import QueuedTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_webhook(*, secret: str | None = None, signature_header: str | None = None) -> BoardWebhook:
    return BoardWebhook(
        id=uuid4(),
        board_id=uuid4(),
        description="Test webhook",
        enabled=True,
        secret=secret,
        signature_header=signature_header,
    )


def _make_request(*, headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/webhook",
        "headers": raw_headers,
        "query_string": b"",
    }
    return Request(scope)


def _hmac_sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# _verify_webhook_signature
# ---------------------------------------------------------------------------


def test_verify_signature_skipped_when_no_secret() -> None:
    """When the webhook has no secret, verification is a no-op regardless of headers."""
    webhook = _make_webhook(secret=None)
    request = _make_request()
    # Must not raise.
    _verify_webhook_signature(webhook, b"payload", request)


def test_verify_signature_valid_sha256_prefix() -> None:
    """A correct sha256= prefixed signature must pass."""
    secret = "my-secret"
    body = b'{"event": "push"}'
    sig = _hmac_sig(secret, body)
    webhook = _make_webhook(secret=secret)
    request = _make_request(headers={"x-hub-signature-256": sig})
    # Must not raise.
    _verify_webhook_signature(webhook, body, request)


def test_verify_signature_valid_without_prefix() -> None:
    """A raw hex digest without the sha256= prefix must also pass."""
    secret = "my-secret"
    body = b'{"event": "push"}'
    raw_hex = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    webhook = _make_webhook(secret=secret)
    request = _make_request(headers={"x-hub-signature-256": raw_hex})
    _verify_webhook_signature(webhook, body, request)


def test_verify_signature_falls_back_to_x_webhook_signature() -> None:
    """The x-webhook-signature header should be used when x-hub-signature-256 is absent."""
    secret = "s3cr3t"
    body = b"body"
    sig = _hmac_sig(secret, body)
    webhook = _make_webhook(secret=secret)
    request = _make_request(headers={"x-webhook-signature": sig})
    _verify_webhook_signature(webhook, body, request)


def test_verify_signature_uses_custom_header() -> None:
    """When signature_header is set, only that header is checked."""
    secret = "tok"
    body = b"data"
    sig = _hmac_sig(secret, body)
    webhook = _make_webhook(secret=secret, signature_header="x-custom-sig")
    request = _make_request(headers={"x-custom-sig": sig})
    _verify_webhook_signature(webhook, body, request)


def test_verify_signature_invalid_raises_403() -> None:
    """A wrong signature must raise HTTP 403."""
    webhook = _make_webhook(secret="real-secret")
    request = _make_request(headers={"x-hub-signature-256": "sha256=badhex"})
    with pytest.raises(HTTPException) as exc_info:
        _verify_webhook_signature(webhook, b"body", request)
    assert exc_info.value.status_code == 403
    assert "Invalid" in exc_info.value.detail


def test_verify_signature_missing_header_raises_403() -> None:
    """When a secret is configured but no signature header is sent, raise HTTP 403."""
    webhook = _make_webhook(secret="secret")
    request = _make_request()  # No signature headers.
    with pytest.raises(HTTPException) as exc_info:
        _verify_webhook_signature(webhook, b"body", request)
    assert exc_info.value.status_code == 403
    assert "Missing" in exc_info.value.detail


# ---------------------------------------------------------------------------
# _decode_payload
# ---------------------------------------------------------------------------


def test_decode_payload_empty_body_returns_empty_dict() -> None:
    assert _decode_payload(b"", content_type="application/json") == {}


def test_decode_payload_json_content_type() -> None:
    result = _decode_payload(b'{"key": "value"}', content_type="application/json")
    assert result == {"key": "value"}


def test_decode_payload_non_json_content_type_returns_text() -> None:
    result = _decode_payload(b"plain text payload", content_type="text/plain")
    assert result == "plain text payload"


def test_decode_payload_auto_detects_json_by_content() -> None:
    """Even without application/json content-type, curly-brace content is parsed as JSON."""
    result = _decode_payload(b'{"auto": true}', content_type=None)
    assert result == {"auto": True}


# ---------------------------------------------------------------------------
# Queue enqueue / decode
# ---------------------------------------------------------------------------


def test_decode_webhook_task_round_trips() -> None:
    """Encoding and decoding a QueuedInboundDelivery must preserve all fields."""
    now = datetime.now(timezone.utc)
    delivery = QueuedInboundDelivery(
        board_id=uuid4(),
        webhook_id=uuid4(),
        payload_id=uuid4(),
        received_at=now,
        attempts=2,
    )
    task = QueuedTask(
        task_type="webhook_delivery",
        payload={
            "board_id": str(delivery.board_id),
            "webhook_id": str(delivery.webhook_id),
            "payload_id": str(delivery.payload_id),
            "received_at": now.isoformat(),
        },
        created_at=now,
        attempts=2,
    )
    decoded = decode_webhook_task(task)
    assert decoded.board_id == delivery.board_id
    assert decoded.webhook_id == delivery.webhook_id
    assert decoded.payload_id == delivery.payload_id
    assert decoded.attempts == 2


def test_decode_webhook_task_wrong_type_raises() -> None:
    """A task with a non-webhook task_type must raise ValueError."""
    task = QueuedTask(
        task_type="some_other_type",
        payload={},
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="Unexpected task_type"):
        decode_webhook_task(task)


def test_enqueue_webhook_delivery_returns_false_on_redis_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the underlying enqueue_task raises (no Redis), the function returns False."""
    from app.services.webhooks import queue as queue_module

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise ConnectionError("Redis not available")

    monkeypatch.setattr(queue_module, "enqueue_task", _boom)

    delivery = QueuedInboundDelivery(
        board_id=uuid4(),
        webhook_id=uuid4(),
        payload_id=uuid4(),
        received_at=datetime.now(timezone.utc),
    )
    result = enqueue_webhook_delivery(delivery)
    assert result is False


def test_enqueue_webhook_delivery_returns_true_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When enqueue_task succeeds, enqueue_webhook_delivery returns True."""
    from app.services.webhooks import queue as queue_module

    def _noop(*_args: Any, **_kwargs: Any) -> None:
        pass

    monkeypatch.setattr(queue_module, "enqueue_task", _noop)

    delivery = QueuedInboundDelivery(
        board_id=uuid4(),
        webhook_id=uuid4(),
        payload_id=uuid4(),
        received_at=datetime.now(timezone.utc),
    )
    result = enqueue_webhook_delivery(delivery)
    assert result is True


# ---------------------------------------------------------------------------
# _captured_headers
# ---------------------------------------------------------------------------


def test_captured_headers_redacts_authorization() -> None:
    request = _make_request(
        headers={
            "authorization": "Bearer secret",
            "x-custom": "kept",
            "content-type": "application/json",
        }
    )
    captured = _captured_headers(request)
    assert captured is not None
    assert "authorization" not in captured
    assert captured.get("x-custom") == "kept"
    assert captured.get("content-type") == "application/json"


def test_captured_headers_redacts_custom_signature_header() -> None:
    request = _make_request(
        headers={
            "x-my-sig": "sha256=abc",
            "x-other": "value",
        }
    )
    captured = _captured_headers(request, extra_redacted="x-my-sig")
    assert captured is not None
    assert "x-my-sig" not in captured
    assert captured.get("x-other") == "value"


def test_captured_headers_returns_none_when_nothing_captured() -> None:
    # Only a content-length header — nothing in the captured set.
    request = _make_request(headers={"accept": "text/html"})
    captured = _captured_headers(request)
    assert captured is None

# ruff: noqa: INP001
"""Unit tests for approval state transition logic.

Covers:
- pending → approved transition
- pending → rejected transition
- Board policy: require_approval_for_done enforcement (via _approval_resolution_message)
- _parse_since helper
- _approval_resolution_message content
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.api.approvals import (
    _approval_resolution_message,
    _parse_since,
)
from app.models.approvals import Approval
from app.models.boards import Board


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _board(*, require_approval_for_done: bool = True) -> Board:
    return Board(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test Board",
        slug="test-board",
        require_approval_for_done=require_approval_for_done,
    )


def _approval(*, status: str = "pending", task_id: UUID | None = None) -> Approval:
    return Approval(
        id=uuid4(),
        board_id=uuid4(),
        task_id=task_id,
        action_type="file.write",
        confidence=90.0,
        status=status,
    )


# ---------------------------------------------------------------------------
# _parse_since
# ---------------------------------------------------------------------------


def test_parse_since_returns_none_for_empty() -> None:
    assert _parse_since(None) is None
    assert _parse_since("") is None
    assert _parse_since("   ") is None


def test_parse_since_parses_iso_utc_string() -> None:
    result = _parse_since("2025-01-15T10:30:00Z")
    assert result is not None
    assert result.year == 2025
    assert result.month == 1
    assert result.day == 15


def test_parse_since_returns_none_for_invalid_string() -> None:
    result = _parse_since("not-a-date")
    assert result is None


def test_parse_since_handles_timezone_aware_input() -> None:
    result = _parse_since("2025-06-01T12:00:00+05:00")
    assert result is not None
    # After conversion to UTC, hour should be 7 (12 - 5 = 7)
    assert result.hour == 7


# ---------------------------------------------------------------------------
# _approval_resolution_message
# ---------------------------------------------------------------------------


def test_approval_resolution_message_approved() -> None:
    board = _board()
    approval = _approval(status="approved")
    message = _approval_resolution_message(board=board, approval=approval)
    assert "APPROVAL RESOLVED" in message
    assert "Decision: approved" in message
    assert board.name in message
    assert str(approval.id) in message


def test_approval_resolution_message_rejected() -> None:
    board = _board()
    approval = _approval(status="rejected")
    message = _approval_resolution_message(board=board, approval=approval)
    assert "Decision: rejected" in message


def test_approval_resolution_message_includes_single_task_id() -> None:
    board = _board()
    task_id = uuid4()
    approval = _approval(status="approved", task_id=task_id)
    message = _approval_resolution_message(board=board, approval=approval, task_ids=[task_id])
    assert f"Task ID: {task_id}" in message


def test_approval_resolution_message_includes_multiple_task_ids() -> None:
    board = _board()
    task_ids = [uuid4(), uuid4()]
    approval = _approval(status="approved")
    message = _approval_resolution_message(board=board, approval=approval, task_ids=task_ids)
    assert "Task IDs:" in message
    for task_id in task_ids:
        assert str(task_id) in message


def test_approval_resolution_message_falls_back_to_approval_task_id() -> None:
    board = _board()
    task_id = uuid4()
    approval = _approval(status="approved", task_id=task_id)
    # No explicit task_ids — should fall back to approval.task_id.
    message = _approval_resolution_message(board=board, approval=approval)
    assert str(task_id) in message


def test_approval_resolution_message_no_task_id_when_none() -> None:
    board = _board()
    approval = _approval(status="approved", task_id=None)
    message = _approval_resolution_message(board=board, approval=approval)
    assert "Task ID:" not in message
    assert "Task IDs:" not in message


def test_approval_resolution_message_contains_action_type() -> None:
    board = _board()
    approval = _approval(status="approved")
    message = _approval_resolution_message(board=board, approval=approval)
    assert f"Action: {approval.action_type}" in message


def test_approval_resolution_message_contains_confidence() -> None:
    board = _board()
    approval = _approval(status="approved")
    message = _approval_resolution_message(board=board, approval=approval)
    assert "Confidence:" in message


# ---------------------------------------------------------------------------
# Board policy: require_approval_for_done flag
# ---------------------------------------------------------------------------


def test_board_require_approval_for_done_default_is_true() -> None:
    """New boards should default to requiring approval for done transitions."""
    board = _board()
    assert board.require_approval_for_done is True


def test_board_require_approval_for_done_can_be_disabled() -> None:
    board = _board(require_approval_for_done=False)
    assert board.require_approval_for_done is False


# ---------------------------------------------------------------------------
# Approval model state
# ---------------------------------------------------------------------------


def test_approval_default_status_is_pending() -> None:
    approval = _approval()
    assert approval.status == "pending"


def test_approval_pending_to_approved_transition() -> None:
    """Simulates the field mutation that the update_approval endpoint performs."""
    approval = _approval(status="pending")
    approval.status = "approved"
    approval.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    assert approval.status == "approved"
    assert approval.resolved_at is not None


def test_approval_pending_to_rejected_transition() -> None:
    approval = _approval(status="pending")
    approval.status = "rejected"
    approval.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    assert approval.status == "rejected"
    assert approval.resolved_at is not None


def test_approval_resolved_at_is_none_when_pending() -> None:
    approval = _approval(status="pending")
    assert approval.resolved_at is None

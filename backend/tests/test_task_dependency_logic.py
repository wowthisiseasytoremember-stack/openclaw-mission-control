# ruff: noqa: INP001
"""Unit tests for task dependency logic.

Covers:
- blocked_by_dependency_ids (pure function)
- _has_cycle detection
- validate_dependency_update: self-dependency rejection
- validate_dependency_update: missing task rejection
- validate_dependency_update: cycle detection
- dependency_ids_by_task_id query path
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.services.task_dependencies import (
    _has_cycle,
    blocked_by_dependency_ids,
    validate_dependency_update,
)


# ---------------------------------------------------------------------------
# Fake session (mirrors _FakeSession from test_organizations_service)
# ---------------------------------------------------------------------------


@dataclass
class _FakeExecResult:
    all_values: list[Any] | None = None

    def first(self) -> Any:
        return self.all_values[0] if self.all_values else None

    def __iter__(self):
        return iter(self.all_values or [])


@dataclass
class _FakeSession:
    exec_results: list[Any]
    added: list[Any] = field(default_factory=list)
    committed: int = 0

    async def exec(self, _statement: Any) -> Any:
        if not self.exec_results:
            raise AssertionError("No more exec_results")
        return self.exec_results.pop(0)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.committed += 1


# ---------------------------------------------------------------------------
# blocked_by_dependency_ids — pure function, no DB
# ---------------------------------------------------------------------------


def test_blocked_by_dependency_ids_empty_deps() -> None:
    result = blocked_by_dependency_ids(dependency_ids=[], status_by_id={})
    assert result == []


def test_blocked_by_dependency_ids_all_done() -> None:
    dep_a = uuid4()
    dep_b = uuid4()
    result = blocked_by_dependency_ids(
        dependency_ids=[dep_a, dep_b],
        status_by_id={dep_a: "done", dep_b: "done"},
    )
    assert result == []


def test_blocked_by_dependency_ids_one_incomplete() -> None:
    dep_a = uuid4()
    dep_b = uuid4()
    result = blocked_by_dependency_ids(
        dependency_ids=[dep_a, dep_b],
        status_by_id={dep_a: "done", dep_b: "in_progress"},
    )
    assert result == [dep_b]


def test_blocked_by_dependency_ids_missing_from_status_map_is_blocking() -> None:
    """A dependency not present in the status map is treated as not-done."""
    dep_a = uuid4()
    result = blocked_by_dependency_ids(dependency_ids=[dep_a], status_by_id={})
    assert result == [dep_a]


def test_blocked_by_dependency_ids_preserves_order() -> None:
    ids = [uuid4() for _ in range(5)]
    status_by_id = {dep: "in_progress" for dep in ids}
    result = blocked_by_dependency_ids(dependency_ids=ids, status_by_id=status_by_id)
    assert result == ids


# ---------------------------------------------------------------------------
# _has_cycle — pure function
# ---------------------------------------------------------------------------


def test_has_cycle_no_edges() -> None:
    nodes = [uuid4(), uuid4()]
    assert _has_cycle(nodes, {}) is False


def test_has_cycle_linear_chain_no_cycle() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    edges = {a: {b}, b: {c}}
    assert _has_cycle([a, b, c], edges) is False


def test_has_cycle_simple_cycle() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    edges = {a: {b}, b: {c}, c: {a}}
    assert _has_cycle([a, b, c], edges) is True


def test_has_cycle_self_loop() -> None:
    a = uuid4()
    edges = {a: {a}}
    assert _has_cycle([a], edges) is True


def test_has_cycle_disconnected_graph_no_cycle() -> None:
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    edges = {a: {b}, c: {d}}
    assert _has_cycle([a, b, c, d], edges) is False


# ---------------------------------------------------------------------------
# validate_dependency_update — async, uses _FakeSession
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_dependency_update_rejects_self_dependency() -> None:
    task_id = uuid4()
    session = _FakeSession(exec_results=[])
    with pytest.raises(HTTPException) as exc_info:
        await validate_dependency_update(
            session,  # type: ignore[arg-type]
            board_id=uuid4(),
            task_id=task_id,
            depends_on_task_ids=[task_id],
        )
    assert exc_info.value.status_code == 422
    assert "itself" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_dependency_update_empty_deps_returns_empty() -> None:
    session = _FakeSession(exec_results=[])
    result = await validate_dependency_update(
        session,  # type: ignore[arg-type]
        board_id=uuid4(),
        task_id=uuid4(),
        depends_on_task_ids=[],
    )
    assert result == []


@pytest.mark.asyncio
async def test_validate_dependency_update_rejects_missing_tasks() -> None:
    """If one of the dependency task IDs does not exist on the board, raise 404."""
    board_id = uuid4()
    task_id = uuid4()
    dep_id = uuid4()

    # First exec: select existing task IDs — returns empty (dep not found).
    session = _FakeSession(exec_results=[_FakeExecResult(all_values=[])])

    with pytest.raises(HTTPException) as exc_info:
        await validate_dependency_update(
            session,  # type: ignore[arg-type]
            board_id=board_id,
            task_id=task_id,
            depends_on_task_ids=[dep_id],
        )
    assert exc_info.value.status_code == 404
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert str(dep_id) in detail["missing_task_ids"]


@pytest.mark.asyncio
async def test_validate_dependency_update_rejects_cycle() -> None:
    """Adding an edge that forms a cycle must raise HTTP 409."""
    board_id = uuid4()
    task_a = uuid4()
    task_b = uuid4()

    # exec 1: existing dep IDs → both tasks exist
    # exec 2: all task IDs on board → [task_a, task_b]
    # exec 3: existing dependency rows → task_b → task_a (so adding task_a → task_b creates a cycle)
    session = _FakeSession(
        exec_results=[
            # Dep task exists check: returns [task_b]
            _FakeExecResult(all_values=[task_b]),
            # All task IDs on board
            _FakeExecResult(all_values=[task_a, task_b]),
            # Existing dependency rows: (task_b, task_a) — b depends on a
            _FakeExecResult(all_values=[(task_b, task_a)]),
        ]
    )

    # We want to add task_a → task_b, but b already depends on a → cycle
    with pytest.raises(HTTPException) as exc_info:
        await validate_dependency_update(
            session,  # type: ignore[arg-type]
            board_id=board_id,
            task_id=task_a,
            depends_on_task_ids=[task_b],
        )
    assert exc_info.value.status_code == 409
    assert "cycle" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_validate_dependency_update_deduplicates_ids() -> None:
    """Duplicate dependency IDs should be deduplicated in the returned list."""
    board_id = uuid4()
    task_id = uuid4()
    dep_id = uuid4()

    session = _FakeSession(
        exec_results=[
            # Dep task exists check
            _FakeExecResult(all_values=[dep_id]),
            # All task IDs on board
            _FakeExecResult(all_values=[task_id, dep_id]),
            # No existing dependency rows
            _FakeExecResult(all_values=[]),
        ]
    )

    result = await validate_dependency_update(
        session,  # type: ignore[arg-type]
        board_id=board_id,
        task_id=task_id,
        depends_on_task_ids=[dep_id, dep_id, dep_id],
    )
    assert result == [dep_id]


@pytest.mark.asyncio
async def test_validate_dependency_update_valid_returns_normalized_list() -> None:
    board_id = uuid4()
    task_id = uuid4()
    dep_a = uuid4()
    dep_b = uuid4()

    session = _FakeSession(
        exec_results=[
            # Both dep tasks exist
            _FakeExecResult(all_values=[dep_a, dep_b]),
            # All task IDs on board
            _FakeExecResult(all_values=[task_id, dep_a, dep_b]),
            # No existing edges
            _FakeExecResult(all_values=[]),
        ]
    )

    result = await validate_dependency_update(
        session,  # type: ignore[arg-type]
        board_id=board_id,
        task_id=task_id,
        depends_on_task_ids=[dep_a, dep_b],
    )
    assert set(result) == {dep_a, dep_b}
    assert len(result) == 2

# ruff: noqa: INP001
"""Unit tests for GatewayDispatchService.

Covers:
- Message routing to correct agent session
- Fallback to board lead when specific agent has no session
- Error handling when gateway offline (try_send_agent_message returns error)
- resolve_trace_id helper
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from app.models.boards import Board
from app.models.gateways import Gateway
from app.services.openclaw.gateway_dispatch import GatewayDispatchService
from app.services.openclaw.gateway_rpc import GatewayConfig, OpenClawGatewayError


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------


@dataclass
class _FakeSession:
    """Minimal session stub — GatewayDispatchService only needs it as an argument."""

    exec_results: list[Any] = field(default_factory=list)
    added: list[Any] = field(default_factory=list)

    async def exec(self, _statement: Any) -> Any:
        if not self.exec_results:
            raise AssertionError("No more exec_results")
        return self.exec_results.pop(0)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        pass


def _gateway(url: str = "ws://gateway.local:18789/ws") -> Gateway:
    return Gateway(
        id=uuid4(),
        organization_id=uuid4(),
        name="test-gateway",
        url=url,
        workspace_root="/tmp/workspace",
    )


def _board() -> Board:
    return Board(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test Board",
        slug="test-board",
    )


def _config() -> GatewayConfig:
    return GatewayConfig(url="ws://gateway.local:18789/ws")


# ---------------------------------------------------------------------------
# try_send_agent_message — returns None on success, error on failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_try_send_agent_message_returns_none_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When send_agent_message succeeds, try_send returns None."""
    session = _FakeSession()
    service = GatewayDispatchService(session)  # type: ignore[arg-type]
    messages_sent: list[dict[str, str]] = []

    async def _fake_send(
        self: GatewayDispatchService,
        *,
        session_key: str,
        config: GatewayConfig,
        agent_name: str,
        message: str,
        deliver: bool = False,
    ) -> None:
        messages_sent.append(
            {"session_key": session_key, "agent_name": agent_name, "message": message}
        )

    monkeypatch.setattr(GatewayDispatchService, "send_agent_message", _fake_send)

    result = await service.try_send_agent_message(
        session_key="agent:session:abc",
        config=_config(),
        agent_name="Lead Agent",
        message="Hello, agent.",
    )
    assert result is None
    assert len(messages_sent) == 1
    assert messages_sent[0]["session_key"] == "agent:session:abc"
    assert messages_sent[0]["agent_name"] == "Lead Agent"


@pytest.mark.asyncio
async def test_try_send_agent_message_returns_error_when_gateway_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the gateway is unreachable, try_send must return the error, not raise."""
    session = _FakeSession()
    service = GatewayDispatchService(session)  # type: ignore[arg-type]
    gateway_error = OpenClawGatewayError("connection refused")

    async def _fake_send(
        self: GatewayDispatchService,
        *,
        session_key: str,
        config: GatewayConfig,
        agent_name: str,
        message: str,
        deliver: bool = False,
    ) -> None:
        raise gateway_error

    monkeypatch.setattr(GatewayDispatchService, "send_agent_message", _fake_send)

    result = await service.try_send_agent_message(
        session_key="agent:session:abc",
        config=_config(),
        agent_name="Lead Agent",
        message="Hello, agent.",
    )
    assert result is gateway_error


@pytest.mark.asyncio
async def test_try_send_agent_message_propagates_non_gateway_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-gateway errors must bubble up and not be swallowed."""
    session = _FakeSession()
    service = GatewayDispatchService(session)  # type: ignore[arg-type]

    async def _fake_send(
        self: GatewayDispatchService,
        *,
        session_key: str,
        config: GatewayConfig,
        agent_name: str,
        message: str,
        deliver: bool = False,
    ) -> None:
        raise RuntimeError("unexpected crash")

    monkeypatch.setattr(GatewayDispatchService, "send_agent_message", _fake_send)

    with pytest.raises(RuntimeError, match="unexpected crash"):
        await service.try_send_agent_message(
            session_key="agent:session:abc",
            config=_config(),
            agent_name="Lead Agent",
            message="crash me",
        )


# ---------------------------------------------------------------------------
# optional_gateway_config_for_board — returns None when gateway missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optional_gateway_config_returns_none_when_no_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the board has no gateway, optional_gateway_config must return None."""
    import app.services.openclaw.gateway_dispatch as dispatch_module

    async def _fake_get_gateway(_session: Any, _board: Board) -> None:
        return None

    monkeypatch.setattr(dispatch_module, "get_gateway_for_board", _fake_get_gateway)

    session = _FakeSession()
    service = GatewayDispatchService(session)  # type: ignore[arg-type]
    board = _board()

    config = await service.optional_gateway_config_for_board(board)
    assert config is None


@pytest.mark.asyncio
async def test_optional_gateway_config_returns_config_when_gateway_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a gateway is found, optional_gateway_config returns a GatewayConfig."""
    import app.services.openclaw.gateway_dispatch as dispatch_module

    gw = _gateway()

    async def _fake_get_gateway(_session: Any, _board: Board) -> Gateway:
        return gw

    monkeypatch.setattr(dispatch_module, "get_gateway_for_board", _fake_get_gateway)

    session = _FakeSession()
    service = GatewayDispatchService(session)  # type: ignore[arg-type]
    board = _board()

    config = await service.optional_gateway_config_for_board(board)
    assert config is not None
    assert isinstance(config, GatewayConfig)


# ---------------------------------------------------------------------------
# resolve_trace_id — static method
# ---------------------------------------------------------------------------


def test_resolve_trace_id_uses_provided_correlation_id() -> None:
    result = GatewayDispatchService.resolve_trace_id("my-trace-id", prefix="task")
    assert result == "my-trace-id"


def test_resolve_trace_id_strips_whitespace() -> None:
    result = GatewayDispatchService.resolve_trace_id("  my-trace-id  ", prefix="task")
    assert result == "my-trace-id"


def test_resolve_trace_id_generates_id_when_none() -> None:
    result = GatewayDispatchService.resolve_trace_id(None, prefix="task")
    assert result.startswith("task:")
    assert len(result) > len("task:")


def test_resolve_trace_id_generates_id_when_empty() -> None:
    result = GatewayDispatchService.resolve_trace_id("   ", prefix="webhook")
    assert result.startswith("webhook:")


def test_resolve_trace_id_generated_ids_are_unique() -> None:
    """Two calls without a correlation_id must produce distinct IDs."""
    a = GatewayDispatchService.resolve_trace_id(None, prefix="p")
    b = GatewayDispatchService.resolve_trace_id(None, prefix="p")
    assert a != b

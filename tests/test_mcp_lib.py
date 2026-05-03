"""Unit tests for mcp_servers._lib (session 1.3)."""
from __future__ import annotations

import pytest

from mcp_servers._lib.client import MCPClient
from mcp_servers._lib.registry import ServerRegistry
from mcp_servers._lib.types import ServerConfig, ToolCall, ToolResult, TransportType


# ---------------------------------------------------------------------------
# types
# ---------------------------------------------------------------------------

def test_server_config_defaults() -> None:
    config = ServerConfig(name="test")
    assert config.transport == TransportType.STDIO
    assert config.command is None
    assert config.url is None
    assert config.env == {}


def test_server_config_stdio() -> None:
    config = ServerConfig(
        name="antaryami",
        transport=TransportType.STDIO,
        command=["python", "-m", "mcp_antaryami"],
    )
    assert config.command == ["python", "-m", "mcp_antaryami"]


def test_server_config_sse() -> None:
    config = ServerConfig(
        name="shilpasutra",
        transport=TransportType.SSE,
        url="http://localhost:8001/sse",
    )
    assert config.url == "http://localhost:8001/sse"


def test_tool_call_defaults() -> None:
    tc = ToolCall(server_name="srv", tool_name="my_tool")
    assert tc.arguments == {}


def test_tool_call_with_arguments() -> None:
    tc = ToolCall(server_name="srv", tool_name="my_tool", arguments={"k": "v"})
    assert tc.arguments == {"k": "v"}


def test_tool_result_defaults() -> None:
    tr = ToolResult(tool_name="my_tool", content=["ok"])
    assert tr.is_error is False


def test_tool_result_error_flag() -> None:
    tr = ToolResult(tool_name="t", content=[], is_error=True)
    assert tr.is_error is True


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

def test_registry_register_and_get() -> None:
    reg = ServerRegistry()
    cfg = ServerConfig(name="antaryami", command=["python", "-m", "antaryami"])
    reg.register(cfg)
    assert reg.get("antaryami") is cfg


def test_registry_get_missing_raises() -> None:
    reg = ServerRegistry()
    with pytest.raises(KeyError, match="not found"):
        reg.get("nonexistent")


def test_registry_all() -> None:
    reg = ServerRegistry()
    reg.register(ServerConfig(name="srv1"))
    reg.register(ServerConfig(name="srv2"))
    assert set(reg.all().keys()) == {"srv1", "srv2"}


def test_registry_all_returns_copy() -> None:
    reg = ServerRegistry()
    reg.register(ServerConfig(name="srv1"))
    snapshot = reg.all()
    reg.register(ServerConfig(name="srv2"))
    assert "srv2" not in snapshot


def test_registry_load_from_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_SERVERS", raising=False)
    reg = ServerRegistry()
    reg.load_from_env()
    assert reg.all() == {}


def test_registry_load_from_env_whitespace_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVERS", "  ")
    reg = ServerRegistry()
    reg.load_from_env()
    assert reg.all() == {}


def test_registry_load_from_env_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVERS", "antaryami")
    monkeypatch.setenv("MCP_ANTARYAMI_TRANSPORT", "stdio")
    monkeypatch.setenv("MCP_ANTARYAMI_COMMAND", "python -m mcp_antaryami")

    reg = ServerRegistry()
    reg.load_from_env()

    assert "antaryami" in reg.all()
    cfg = reg.get("antaryami")
    assert cfg.transport == TransportType.STDIO
    assert cfg.command == ["python", "-m", "mcp_antaryami"]


def test_registry_load_from_env_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVERS", "shilpasutra")
    monkeypatch.setenv("MCP_SHILPASUTRA_TRANSPORT", "sse")
    monkeypatch.setenv("MCP_SHILPASUTRA_URL", "http://localhost:8001/sse")

    reg = ServerRegistry()
    reg.load_from_env()

    cfg = reg.get("shilpasutra")
    assert cfg.transport == TransportType.SSE
    assert cfg.url == "http://localhost:8001/sse"


def test_registry_load_from_env_multiple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVERS", "antaryami,shilpasutra")
    monkeypatch.setenv("MCP_ANTARYAMI_TRANSPORT", "stdio")
    monkeypatch.setenv("MCP_ANTARYAMI_COMMAND", "python -m mcp_antaryami")
    monkeypatch.setenv("MCP_SHILPASUTRA_TRANSPORT", "sse")
    monkeypatch.setenv("MCP_SHILPASUTRA_URL", "http://localhost:8001/sse")

    reg = ServerRegistry()
    reg.load_from_env()

    assert set(reg.all().keys()) == {"antaryami", "shilpasutra"}


def test_registry_load_from_env_extra_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVERS", "karaveda")
    monkeypatch.setenv("MCP_KARAVEDA_TRANSPORT", "stdio")
    monkeypatch.setenv("MCP_KARAVEDA_COMMAND", "python -m mcp_karaveda")
    monkeypatch.setenv("MCP_KARAVEDA_ENV_GST_KEY", "abc123")
    monkeypatch.setenv("MCP_KARAVEDA_ENV_REGION", "IN")

    reg = ServerRegistry()
    reg.load_from_env()

    cfg = reg.get("karaveda")
    assert cfg.env == {"GST_KEY": "abc123", "REGION": "IN"}


def test_registry_load_from_env_default_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVERS", "vidyalaya")
    monkeypatch.setenv("MCP_VIDYALAYA_COMMAND", "python -m mcp_vidyalaya")
    monkeypatch.delenv("MCP_VIDYALAYA_TRANSPORT", raising=False)

    reg = ServerRegistry()
    reg.load_from_env()

    cfg = reg.get("vidyalaya")
    assert cfg.transport == TransportType.STDIO


# ---------------------------------------------------------------------------
# client (no real server needed — only tests guard logic)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_list_tools_not_connected_raises() -> None:
    cfg = ServerConfig(name="test", command=["echo"])
    client = MCPClient(cfg)
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.list_tools()


@pytest.mark.asyncio
async def test_client_call_tool_not_connected_raises() -> None:
    cfg = ServerConfig(name="test", command=["echo"])
    client = MCPClient(cfg)
    tc = ToolCall(server_name="test", tool_name="noop")
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.call_tool(tc)


@pytest.mark.asyncio
async def test_client_connect_stdio_missing_command_raises() -> None:
    cfg = ServerConfig(name="test", transport=TransportType.STDIO, command=None)
    client = MCPClient(cfg)
    with pytest.raises(ValueError, match="command"):
        await client.connect()


@pytest.mark.asyncio
async def test_client_connect_sse_missing_url_raises() -> None:
    cfg = ServerConfig(name="test", transport=TransportType.SSE, url=None)
    client = MCPClient(cfg)
    with pytest.raises(ValueError, match="url"):
        await client.connect()


@pytest.mark.asyncio
async def test_client_disconnect_idempotent() -> None:
    """disconnect() on a never-connected client must not raise."""
    cfg = ServerConfig(name="test", command=["echo"])
    client = MCPClient(cfg)
    await client.disconnect()  # no-op, must not raise

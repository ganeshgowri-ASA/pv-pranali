from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_servers._lib.types import ServerConfig, ToolCall, ToolResult, TransportType


class MCPClient:
    """Async MCP client wrapping modelcontextprotocol/python-sdk.

    Usage::

        client = MCPClient(config)
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool(ToolCall(...))
        await client.disconnect()
    """

    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def connect(self) -> None:
        """Open transport and initialize MCP session."""
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        if self._config.transport == TransportType.STDIO:
            if not self._config.command:
                raise ValueError("stdio transport requires 'command' in ServerConfig")
            params = StdioServerParameters(
                command=self._config.command[0],
                args=self._config.command[1:],
                env=self._config.env or None,
            )
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:
            if not self._config.url:
                raise ValueError("sse transport requires 'url' in ServerConfig")
            read, write = await self._stack.enter_async_context(
                sse_client(self._config.url)
            )

        self._session = await self._stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return all tools advertised by the connected server."""
        if self._session is None:
            raise RuntimeError("Not connected; call connect() first")
        result = await self._session.list_tools()
        return [t.model_dump() for t in result.tools]

    async def call_tool(self, tool_call: ToolCall) -> ToolResult:
        """Invoke a tool on the connected server."""
        if self._session is None:
            raise RuntimeError("Not connected; call connect() first")
        result = await self._session.call_tool(
            tool_call.tool_name, tool_call.arguments
        )
        return ToolResult(
            tool_name=tool_call.tool_name,
            content=result.content,
            is_error=bool(result.isError),
        )

    async def disconnect(self) -> None:
        """Close session and transport."""
        if self._stack is not None:
            await self._stack.__aexit__(None, None, None)
            self._stack = None
            self._session = None

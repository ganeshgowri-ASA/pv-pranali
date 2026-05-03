"""Shared MCP server base utilities for pv-pranali."""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP as _FastMCP

    class MCPClient(_FastMCP):
        """Base MCP server wrapper for pv-pranali servers."""
        pass

except ImportError:  # graceful degradation when mcp not installed
    class MCPClient:  # type: ignore[no-redef]
        def __init__(self, name: str, **kwargs):
            self.name = name
            self._tools: dict = {}

        def tool(self):
            def decorator(fn):
                self._tools[fn.__name__] = fn
                return fn
            return decorator

        def run(self):
            raise RuntimeError("Install 'mcp' package: pip install mcp")

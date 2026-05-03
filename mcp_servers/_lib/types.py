from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"


class ServerConfig(BaseModel):
    name: str
    transport: TransportType = TransportType.STDIO
    command: list[str] | None = None
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class ToolCall(BaseModel):
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    content: list[Any]
    is_error: bool = False

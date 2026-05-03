from __future__ import annotations

import os

from mcp_servers._lib.types import ServerConfig, TransportType


class ServerRegistry:
    """Maps server names to their connection configs."""

    def __init__(self) -> None:
        self._configs: dict[str, ServerConfig] = {}

    def register(self, config: ServerConfig) -> None:
        self._configs[config.name] = config

    def get(self, name: str) -> ServerConfig:
        try:
            return self._configs[name]
        except KeyError:
            raise KeyError(f"Server '{name}' not found in registry")

    def all(self) -> dict[str, ServerConfig]:
        return dict(self._configs)

    def load_from_env(self) -> None:
        """
        Populate registry from environment variables.

        Expected format:
            MCP_SERVERS=name1,name2
            MCP_{NAME}_TRANSPORT=stdio|sse
            MCP_{NAME}_COMMAND=python -m some_module   # stdio only
            MCP_{NAME}_URL=http://host:port/sse        # sse only
            MCP_{NAME}_ENV_{VAR}=value                 # extra env vars passed to server
        """
        servers_raw = os.environ.get("MCP_SERVERS", "")
        if not servers_raw.strip():
            return

        for name in servers_raw.split(","):
            name = name.strip()
            if not name:
                continue

            key = name.upper()
            transport_str = os.environ.get(f"MCP_{key}_TRANSPORT", "stdio")
            transport = TransportType(transport_str.lower())

            command_str = os.environ.get(f"MCP_{key}_COMMAND", "")
            command: list[str] | None = command_str.split() if command_str else None

            url: str | None = os.environ.get(f"MCP_{key}_URL")

            env_prefix = f"MCP_{key}_ENV_"
            env: dict[str, str] = {
                k[len(env_prefix):]: v
                for k, v in os.environ.items()
                if k.startswith(env_prefix)
            }

            self.register(
                ServerConfig(
                    name=name,
                    transport=transport,
                    command=command,
                    url=url,
                    env=env,
                )
            )

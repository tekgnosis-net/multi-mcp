from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Dict, Optional, Any
from copy import deepcopy
import os

import anyio

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from src.utils.logger import get_logger

# Encoding defaults for stdio clients (mirrors mcp.client.stdio.StdioServerParameters defaults)
DEFAULT_ENCODING: str = "utf-8"
DEFAULT_ENCODING_ERROR_HANDLER: str = "strict"


@dataclass
class ManagedClient:
    """Wrapper holding the session and its dedicated exit stack."""

    name: str
    session: ClientSession
    stack: Optional[AsyncExitStack]
    config: Dict[str, Any]
    external: bool = False


class MCPClientManager:
    """Lifecycle manager for MCP client sessions (stdio or SSE)."""

    def __init__(self):
        self.clients: Dict[str, ManagedClient] = {}
        self.logger = get_logger("ClientManager")

    async def create_clients(self, config: dict) -> Dict[str, ClientSession]:
        """Create all clients from a config mapping."""

        for name, server_config in config.get("mcpServers", {}).items():
            await self.add_client(name, server_config)

        return {name: managed.session for name, managed in self.clients.items()}

    async def add_client(self, name: str, server_config: dict) -> Optional[ClientSession]:
        """Create and register a single client."""

        if name in self.clients:
            self.logger.warning(f"⚠️ Client '{name}' already exists and will be replaced.")
            await self.remove_client(name)

        stack = AsyncExitStack()
        await stack.__aenter__()

        try:
            session = await self._create_session(stack, name, server_config)
        except Exception as exc:  # pragma: no cover - propagated for logging
            await stack.aclose()
            self.logger.error(f"❌ Failed to create client for {name}: {exc}")
            return None

        self.clients[name] = ManagedClient(name=name, session=session, stack=stack, config=deepcopy(server_config), external=False)
        self.logger.info(f"✅ Connected to {name}")
        return session

    async def remove_client(self, name: str) -> None:
        """Remove and close a managed client if it exists."""

        managed = self.clients.pop(name, None)
        if not managed:
            self.logger.warning(f"⚠️ Tried to remove unknown client '{name}'")
            return

        self.logger.info(f"🗑️ Closing client '{name}'")

        # Ensure the client session is closed before tearing down transports.
        try:
            await managed.session.close()
        except Exception as exc:  # pragma: no cover - defensive shutdown
            self.logger.warning(f"⚠️ Error while closing session for '{name}': {exc}")

        if managed.stack and not managed.external:
            try:
                # Shield the cleanup from anyio cancellation so that removing a client
                # during a config hot-reload (which runs inside a task group cancel scope)
                # doesn't propagate CancelledError and crash the server.
                with anyio.CancelScope(shield=True):
                    await managed.stack.aclose()
            except Exception as exc:
                self.logger.warning(
                    "⚠️ AsyncExitStack close for '%s' raised %s; continuing with best-effort cleanup.",
                    name,
                    exc,
                )

    async def update_clients(self, config: dict) -> Dict[str, ClientSession]:
        """Reconcile active clients with a new configuration."""

        desired = config.get("mcpServers", {})
        current = set(self.clients.keys())
        desired_names = set(desired.keys())

        # Remove missing entries
        for name in current - desired_names:
            await self.remove_client(name)

        # Add or replace updated entries
        for name in desired_names:
            existing = self.clients.get(name)
            if not existing or existing.config != desired[name]:
                await self.add_client(name, desired[name])

        return self.sessions

    def get_client(self, name: str) -> Optional[ClientSession]:
        """Retrieve a client session by name."""

        managed = self.clients.get(name)
        return managed.session if managed else None

    @property
    def sessions(self) -> Dict[str, ClientSession]:
        """Current live client sessions keyed by name."""

        return {name: managed.session for name, managed in self.clients.items()}

    def client_configs(self) -> Dict[str, Dict[str, Any]]:
        """Expose stored configs for external diffing when needed."""

        return {name: deepcopy(managed.config) for name, managed in self.clients.items()}

    async def close(self) -> None:
        """Close all clients and release resources."""

        for name in list(self.clients.keys()):
            await self.remove_client(name)

    def attach_existing(self, name: str, session: ClientSession, config: Optional[dict] = None) -> None:
        """Attach a pre-created client session (used primarily for tests)."""

        self.clients[name] = ManagedClient(
            name=name,
            session=session,
            stack=None,
            config=deepcopy(config or {}),
            external=True,
        )

    async def _create_session(self, stack: AsyncExitStack, name: str, server: dict) -> ClientSession:
        """Create a session for the given server configuration."""

        command = server.get("command")
        url = server.get("url")
        args = server.get("args", [])
        env = server.get("env", {})
        encoding = server.get("encoding", DEFAULT_ENCODING)
        encoding_error_handler = server.get("encoding_error_handler", DEFAULT_ENCODING_ERROR_HANDLER)

        merged_env = os.environ.copy()
        merged_env.update(env)

        if command:
            self.logger.info(f"🔌 Creating stdio client for {name}")
            params = StdioServerParameters(
                command=command,
                args=args,
                env=merged_env,
                encoding=encoding,
                encoding_error_handler=encoding_error_handler,
            )
            read, write = await stack.enter_async_context(stdio_client(params))
        elif url:
            self.logger.info(f"🌐 Creating SSE client for {name}")
            read, write = await stack.enter_async_context(sse_client(url=url))
        else:
            raise ValueError(f"Client '{name}' missing 'command' or 'url'")

        session = await stack.enter_async_context(ClientSession(read, write))
        return session

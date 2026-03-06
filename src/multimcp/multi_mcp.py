import os
import contextlib
import uvicorn
import json
import anyio
from collections.abc import AsyncIterator
from typing import Literal, Any, Optional
from copy import deepcopy
from pathlib import Path

from pydantic_settings import BaseSettings
from watchfiles import awatch

from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.staticfiles import StaticFiles

from src.multimcp.mcp_client import MCPClientManager
from src.multimcp.mcp_proxy import MCPProxyServer
from src.utils.logger import configure_logging, get_logger

class MCPSettings(BaseSettings):
    """Configuration settings for the MultiMCP server."""
    host: str = "127.0.0.1"
    port: int = 8080
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    transport: Literal["stdio", "sse", "http"] = "http"
    http_server_debug: bool = False
    config: str="./mcp.json"

class MultiMCP:
    def __init__(self, **settings: Any):
        self.settings = MCPSettings(**settings)
        configure_logging(level=self.settings.log_level)
        self.logger = get_logger("MultiMCP")
        self.proxy: Optional[MCPProxyServer] = None
        self.client_manager = MCPClientManager()
        self.current_config: dict[str, Any] = {"mcpServers": {}}
        self.config_path = self.settings.config
        project_root = Path(__file__).resolve().parent.parent.parent
        configured_dist = os.environ.get("FRONTEND_DIST")
        self.frontend_dist = Path(configured_dist) if configured_dist else project_root / "frontend" / "dist"
        self.sse_transport = SseServerTransport("/mcp")  # legacy SSE (kept for backward compat)
        self.session_manager: Optional[StreamableHTTPSessionManager] = None  # streamable HTTP


    async def run(self):
        """Entry point to run the MultiMCP server: loads config, initializes clients, starts server."""
        self.logger.info(f"🚀 Starting MultiMCP with transport: {self.settings.transport}")
        config = self.load_mcp_config(path=self.settings.config)
        if not config:
            self.logger.error("❌ Failed to load MCP config.")
            return
        self.current_config = config

        clients = await self.client_manager.create_clients(config)
        if not clients:
            self.logger.error("❌ No valid clients were created.")
            return

        self.logger.info(f"✅ Connected clients: {list(clients.keys())}")

        try:
            self.proxy = await MCPProxyServer.create(self.client_manager)

            await self.start_server()
        finally:
            await self.client_manager.close()


    def load_mcp_config(self,path="./mcp.json"):
        """Loads MCP JSON configuration From File."""
        if not os.path.exists(path):
            print(f"Error: {path} does not exist.")
            return None

        with open(path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                if "mcpServers" not in data:
                    data["mcpServers"] = {}
                return data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                return None


    async def start_server(self):
        """Start the proxy server in stdio or SSE mode."""
        if self.settings.transport == "stdio":
            await self.start_stdio_server()
        elif self.settings.transport in {"sse", "http"}:
            await self.start_http_server()
        else:
            raise ValueError(f"Unsupported transport: {self.settings.transport}")

    async def start_stdio_server(self) -> None:
        """Run the proxy server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await self.proxy.run(
                read_stream,
                write_stream,
                self.proxy.create_initialization_options(),
            )

    async def start_http_server(self) -> None:
        """Run the proxy over Streamable HTTP (MCP 2025-11-25) with a legacy /sse fallback."""

        # Streamable HTTP session manager — MCP 2025-11-25 compliant transport
        self.session_manager = StreamableHTTPSessionManager(app=self.proxy)

        @contextlib.asynccontextmanager
        async def lifespan(_app: Any) -> AsyncIterator[None]:
            async with self.session_manager.run():
                yield

        api_routes = [
            Route("/health", endpoint=self.handle_health, methods=["GET"]),
            Route("/config", endpoint=self.handle_config, methods=["GET", "PUT"]),
            Route("/servers", endpoint=self.handle_servers, methods=["GET", "POST"]),
            Route("/servers/{name}", endpoint=self.handle_single_server, methods=["GET", "DELETE"]),
            Route("/stats", endpoint=self.handle_stats, methods=["GET"]),
            Route("/tools", endpoint=self.handle_tools, methods=["GET"]),
        ]

        routes = [
            # Primary MCP endpoint: Streamable HTTP (MCP 2025-11-25 spec)
            Route("/mcp", endpoint=self.handle_mcp_streamable, methods=["GET", "POST", "DELETE"]),
            # Legacy SSE endpoint kept for backward-compatible clients
            Route("/sse", endpoint=self.handle_sse_connection, methods=["GET"]),
            Mount("/api", routes=api_routes),
        ]

        if self.frontend_dist.exists():
            routes.append(
                Mount(
                    "/",
                    app=StaticFiles(directory=self.frontend_dist, html=True),
                    name="frontend",
                )
            )
        else:
            self.logger.warning(
                "⚠️ Frontend build directory not found at %s; serving API only.",
                self.frontend_dist,
            )
            routes.append(Route("/", endpoint=self.handle_frontend_missing, methods=["GET"]))

        starlette_app = Starlette(
            debug=self.settings.http_server_debug,
            routes=routes,
            lifespan=lifespan,
        )

        config = uvicorn.Config(
            starlette_app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=self.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)

        # Run the HTTP server and the config-file watcher concurrently
        async with anyio.create_task_group() as tg:
            tg.start_soon(server.serve)
            tg.start_soon(self._watch_config)

    async def handle_health(self, _: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def handle_config(self, request: Request) -> JSONResponse:
        if request.method == "GET":
            return JSONResponse({"config": self.current_config})

        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON payload"}, status_code=400)

        if not isinstance(payload, dict):
            return JSONResponse({"error": "Config payload must be an object"}, status_code=400)

        if "mcpServers" in payload and not isinstance(payload["mcpServers"], dict):
            return JSONResponse({"error": "'mcpServers' must be an object"}, status_code=400)

        result = await self.apply_config(payload, persist=True)
        return JSONResponse({"message": "Configuration updated", "result": result})

    async def handle_servers(self, request: Request) -> JSONResponse:
        if not self.proxy:
            return JSONResponse({"error": "Proxy not initialized"}, status_code=500)
        if request.method == "GET":
            return JSONResponse({"servers": self.proxy.list_server_overview()})

        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON payload"}, status_code=400)

        servers_patch = payload.get("mcpServers")
        if not isinstance(servers_patch, dict):
            return JSONResponse({"error": "Expected 'mcpServers' object"}, status_code=400)

        merged_config = deepcopy(self.current_config) if self.current_config else {"mcpServers": {}}
        merged_config.setdefault("mcpServers", {}).update(servers_patch)

        result = await self.apply_config(merged_config, persist=True)
        return JSONResponse({"message": "Servers updated", "result": result})

    async def handle_single_server(self, request: Request) -> JSONResponse:
        name = request.path_params.get("name")
        if not name:
            return JSONResponse({"error": "Missing server name"}, status_code=400)

        if not self.proxy:
            return JSONResponse({"error": "Proxy not initialized"}, status_code=500)

        if request.method == "GET":
            overview = self.proxy.list_server_overview().get(name)
            if not overview:
                return JSONResponse({"error": f"Server '{name}' not found"}, status_code=404)
            return JSONResponse({"name": name, **overview})

        if name not in self.current_config.get("mcpServers", {}):
            return JSONResponse({"error": f"Server '{name}' not present"}, status_code=404)

        updated_config = deepcopy(self.current_config)
        updated_config["mcpServers"].pop(name, None)

        result = await self.apply_config(updated_config, persist=True)
        return JSONResponse({"message": f"Server '{name}' removed", "result": result})

    async def handle_stats(self, _: Request) -> JSONResponse:
        if not self.proxy:
            return JSONResponse({"error": "Proxy not initialized"}, status_code=500)
        return JSONResponse({"stats": self.proxy.list_server_overview()})

    async def handle_tools(self, _: Request) -> JSONResponse:
        if not self.proxy:
            return JSONResponse({"error": "Proxy not initialized"}, status_code=500)
        tools_overview = {}
        for server_name, client in self.client_manager.sessions.items():
            try:
                tools = await client.list_tools()
                tools_overview[server_name] = [tool.name for tool in tools.tools]
            except Exception as exc:  # pragma: no cover - rely on logs
                tools_overview[server_name] = {"error": str(exc)}

        return JSONResponse({"tools": tools_overview})

    async def handle_mcp_streamable(self, request: Request) -> Response:
        """Handle MCP requests via the Streamable HTTP transport (MCP 2025-11-25 spec)."""
        if not self.session_manager:
            return JSONResponse({"error": "Server not initialized"}, status_code=500)
        # session_manager writes the full ASGI response directly via send; return a
        # no-body sentinel so Starlette's Route wrapper doesn't attempt a second send.
        await self.session_manager.handle_request(request.scope, request.receive, request._send)
        return Response(status_code=200)

    async def handle_sse_connection(self, request: Request) -> Response:
        """Legacy SSE endpoint, kept for backward-compatible MCP clients."""
        if not self.proxy:
            return JSONResponse({"error": "Proxy not initialized"}, status_code=500)

        try:
            async with self.sse_transport.connect_sse(
                request.scope,
                request.receive,
                request._send,
            ) as (read_stream, write_stream):
                await self.proxy.run(
                    read_stream,
                    write_stream,
                    self.proxy.create_initialization_options(),
                )
        except Exception as exc:  # pragma: no cover - best-effort logging
            self.logger.error("❌ SSE session error: %s", exc)
            return JSONResponse(
                {"error": "SSE session terminated", "details": str(exc)},
                status_code=500,
            )

        # Streaming already handled; return empty success when session closes.
        return Response(status_code=204)

    async def _watch_config(self) -> None:
        """Watch the MCP config file and hot-reload on any change."""
        config_path = Path(self.config_path).resolve()
        if not config_path.exists():
            self.logger.warning("⚠️ Config file not found for watching: %s", config_path)
            return
        self.logger.info("👁️  Watching config: %s", config_path)
        async for _ in awatch(str(config_path)):
            self.logger.info("🔄 Config file changed, reloading …")
            new_config = self.load_mcp_config(str(config_path))
            if not new_config:
                self.logger.error("❌ Reloaded config is invalid; skipping.")
                continue
            try:
                result = await self.apply_config(new_config, persist=False)
                self.logger.info("✅ Config reloaded: %s", result)
            except Exception as exc:
                self.logger.error("❌ Config reload failed: %s", exc)

    async def handle_frontend_missing(self, _: Request) -> JSONResponse:
        return JSONResponse(
            {
                "error": "Frontend assets not available",
                "hint": "Build the UI with 'npm run build' inside frontend/ or set FRONTEND_DIST.",
            },
            status_code=503,
        )

    async def apply_config(self, new_config: dict, persist: bool) -> dict[str, list[str]]:
        """Apply a new configuration and optionally persist it to disk."""

        if not self.proxy:
            raise RuntimeError("Proxy not initialized")

        current_servers = self.current_config.get("mcpServers", {})
        desired_servers = new_config.get("mcpServers", {})

        if not isinstance(desired_servers, dict):
            raise ValueError("Configuration must include an 'mcpServers' object")

        current_names = set(current_servers.keys())
        desired_names = set(desired_servers.keys())

        removed = sorted(current_names - desired_names)
        added = sorted(desired_names - current_names)
        potentially_updated = current_names & desired_names
        updated = sorted([name for name in potentially_updated if current_servers[name] != desired_servers[name]])

        # Remove dropped/updated servers
        for name in removed + updated:
            await self.proxy.unregister_client(name)
            await self.client_manager.remove_client(name)

        # Add or recreate servers
        for name in added + updated:
            session = await self.client_manager.add_client(name, desired_servers[name])
            if session:
                await self.proxy.register_client(name, session)

        self.current_config = deepcopy(new_config)

        if persist:
            self.persist_config(new_config)

        return {"added": added, "removed": removed, "updated": updated}

    def persist_config(self, config: dict) -> None:
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=2, sort_keys=True)
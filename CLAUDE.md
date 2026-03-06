# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-MCP is a Python-based proxy server that acts as a single MCP (Model Context Protocol) server while connecting to and routing between multiple backend MCP servers. It supports STDIO, SSE, and HTTP transports and can dynamically add/remove MCP servers at runtime.

## Architecture

### Core Components

- **MultiMCP (`src/multimcp/multi_mcp.py`)**: Main server orchestrator that handles configuration, transport modes, and HTTP endpoints
- **MCPProxyServer (`src/multimcp/mcp_proxy.py`)**: Core proxy that forwards MCP requests to backend servers, handles tool namespacing (`server_name_tool_name`), and manages capabilities aggregation
- **MCPClientManager (`src/multimcp/mcp_client.py`)**: Manages lifecycle of multiple MCP client connections (both stdio and SSE)
- **Logger (`src/utils/logger.py`)**: Centralized logging using Rich handlers with `multi_mcp.*` namespace

### Key Patterns

- **Tool Namespacing**: Tools are namespaced as `server_name_tool_name` to avoid conflicts when multiple servers expose tools with the same name
- **Transport Flexibility**: Supports STDIO (pipe-based), SSE (legacy), and HTTP/Streamable-HTTP (default) transports
- **Dynamic Server Management**: Can add/remove MCP servers at runtime via the HTTP management API (`/api/servers`)
- **Config File Watching**: `mcp.json` is watched via `watchfiles`; any change is auto-applied without a restart
- **Capability Aggregation**: Proxies and combines tools, prompts, and resources from all connected backend servers

## Development Commands

### Running the Server
```bash
# HTTP mode (default) — binds to 127.0.0.1:8080
uv run main.py --transport http

# HTTP mode with explicit host/port
uv run main.py --transport http --host 0.0.0.0 --port 8096

# STDIO mode for pipe-based agents
uv run main.py --transport stdio

# With custom config file
uv run main.py --config ./examples/config/mcp_k8s.json

# Quick development run (HTTP, default config)
make run
```

### Testing
```bash
# Individual test suites
make test-proxy      # Core proxy functionality  
make test-e2e        # End-to-end integration tests
make test-lifecycle  # Client lifecycle management
make test-k8s        # Kubernetes deployment tests (requires docker-build)

# All tests
make all-test

# Run specific test file directly
pytest -s tests/proxy_test.py
```

### Docker & Kubernetes
```bash
# Build and run locally
make docker-build
make docker-run

# Kubernetes with Kind
kind create cluster --name multi-mcp-test
kind load docker-image multi-mcp --name multi-mcp-test
kubectl apply -f examples/k8s/multi-mcp.yaml
```

### Docker Container Details
- **Base Image**: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` (Debian-based)
- **Node.js Runtime**: Node.js 20.x installed for MCP servers requiring Node runtime
- **Production Config**: `./config/mcp.json` is copied to `/app/mcp.json` at build time; currently configured with `mcp-sequentialthinking-tools`, `searxng`, and `time` servers
- **Default Port**: `8096` (set via `MCP_PORT` env var)
- **Network**: Binds to `0.0.0.0` for container accessibility
- **Frontend**: React/Vite UI is built during `docker build` and served from `/app/frontend/dist`

### Dependency Management
```bash
# Install dependencies
uv venv
uv pip install -r requirements.txt

# Alternative: Direct run (handles dependencies automatically)
uv run main.py
```

## Configuration

### MCP Server Configuration
Configuration is JSON-based, defining backend MCP servers to connect to:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["./tools/get_weather.py"],
      "env": {"API_KEY": "value"}
    },
    "remote_service": {
      "url": "http://127.0.0.1:9080/sse"
    }
  }
}
```

### Runtime HTTP API
Available when running with `--transport http` (or `sse`). MCP transport endpoints:
- `GET|POST|DELETE /mcp` — **Streamable HTTP** (MCP 2025-11-25 spec); primary MCP endpoint
- `GET /sse` — **Legacy SSE** connection for older MCP clients (kept for backward compat)

Management API (prefixed `/api`):
- `GET /api/health` — liveness probe
- `GET /api/config`, `PUT /api/config` — read / hot-reload full config
- `GET /api/servers`, `POST /api/servers` — list / add servers
- `GET /api/servers/{name}`, `DELETE /api/servers/{name}` — inspect / remove a server
- `GET /api/stats` — per-server telemetry snapshot
- `GET /api/tools` — tools list grouped by server

## Code Conventions

### Error Handling
- Use Rich logging with emoji prefixes: `✅ success`, `❌ errors`, `⚠️ warnings`
- Log errors but don't raise exceptions for individual server failures
- Gracefully handle missing tools/prompts/resources with appropriate error responses
- **Capability Checks**: Always verify server capabilities before calling MCP methods to avoid "Method not found" errors

### Async Patterns
- Use `AsyncExitStack` for managing multiple client lifecycles
- Prefer `async with` for resource management
- Always await client operations and handle exceptions per-client

### Type Hints
- Use `from typing import` imports for type annotations
- Prefer `Optional[Type]` over `Type | None` for Python 3.10 compatibility
- Use `Literal` for string enums (transport modes, log levels)

## Development Notes

### Tool Namespacing Implementation
Tools are internally namespaced using `_make_key()` and `_split_key()` static methods in `MCPProxyServer`:
- `_make_key(server_name, tool_name)` creates `server_name_tool_name` identifiers
- `_split_key(key)` splits namespaced keys back into `(server, tool)` tuples using first underscore
- Namespaced tools are stored in `tool_to_server` dict mapping keys to `ToolMapping` objects
- This allows multiple servers to expose tools with identical base names without conflicts

### Capability Management
- Server capabilities are checked during initialization and stored in `self.capabilities[name]`
- `_list_prompts()` and `_list_resources()` only call servers that support those capabilities
- Prevents "Method not found" errors when servers don't implement all MCP methods
- Graceful handling of servers with different capability sets (tools-only vs full MCP servers)

### Transport Modes
- **STDIO**: Pipe-based communication for CLI tools and local agents
- **SSE** (legacy, `/sse`): HTTP Server-Sent Events kept for backward-compatible clients; backed by `mcp.server.sse.SseServerTransport`
- **HTTP / Streamable HTTP** (default, `/mcp`): MCP 2025-11-25 spec transport via `StreamableHTTPSessionManager`; supports stateful and stateless sessions, resumable SSE streams, and JSON-response mode

### Config File Watching
`MultiMCP` uses `watchfiles.awatch` to watch the config JSON file at the path supplied by `--config`. Any write to that file triggers `apply_config(..., persist=False)`, which hot-swaps added/removed/changed servers without restarting the process. The watcher runs as a concurrent task alongside the uvicorn server inside `anyio.create_task_group()`.

### Testing Strategy
- **Unit tests**: Focus on individual components (proxy, client manager)
- **Integration tests**: End-to-end flows with real MCP tools
- **K8s tests**: Deployment and service exposure validation

### Project Structure
- `main.py` - Entry point CLI interface using `MultiMCP` class
- `src/multimcp/multi_mcp.py` - Main orchestrator with `MCPSettings` and HTTP endpoints
- `src/multimcp/mcp_proxy.py` - Core proxy server with request forwarding and capability aggregation
- `src/multimcp/mcp_client.py` - Client lifecycle management using `AsyncExitStack`
- `src/utils/logger.py` - Centralized Rich logging with `multi_mcp.*` namespace
- `frontend/` - React/TypeScript/Vite dashboard UI (`npm run build` outputs to `frontend/dist/`)
- `apps/` - Standalone helper MCP apps (e.g. `whereami-mcp.py`)
- `config/mcp.json` - Active production config (copied into container as `/app/mcp.json`)
- `tests/` - Comprehensive test suite with mock MCP servers and fixtures
- `examples/config/` - Sample configuration files for different deployment scenarios

### Dependencies
Key dependencies include:
- `mcp>=1.26.0` - Core MCP protocol implementation (Streamable HTTP, SSE, stdio transports; MCP 2025-11-25 spec)
- `langchain-mcp-adapters` - LangChain integration utilities (no longer imported inside `mcp_client.py`; encoding defaults are defined locally)
- `starlette` + `uvicorn` - ASGI HTTP server
- `watchfiles` - Async file-system watcher for config hot-reload
- `httpx-sse` - SSE client support
- `rich` - Enhanced logging and console output
- `pytest` + `pytest-asyncio` - Testing framework with async support

## MCP Server Status & Testing

### Configured MCP Servers (config/mcp.json)

**Sequential Thinking Tools**
- **Server**: `mcp-sequentialthinking-tools` (Node.js via `npx -y mcp-sequentialthinking-tools`)
- **Tool Prefix**: `mcp-sequentialthinking-tools_*`
- **Capabilities**: Structured multi-step reasoning
- **Env**: `MAX_HISTORY_SIZE=10000`

**SearXNG Web Search**
- **Server**: `searxng` (Node.js via `npx -y @kevinwatt/mcp-server-searxng`)
- **Tool Prefix**: `searxng_*`
- **Capabilities**: Privacy-respecting meta-search via configured SearXNG instance
- **Env**: `SEARXNG_INSTANCES`, `SEARXNG_USER_AGENT`

**Time Server**
- **Server**: `time` (Python via `uvx mcp-server-time`)
- **Tool Prefix**: `time_*`
- **Capabilities**: Current time/date with timezone support (default: `Australia/Sydney`)

### Tool Namespacing in Action
All MCP tools are accessible through the multi-mcp proxy with the naming pattern:
`{server_name}_{tool_name}`

Example: `searxng_search`, `time_get_current_time`, `mcp-sequentialthinking-tools_sequentialthinking`

### Verification Status
- **Last Updated**: 2026-03-07
- **Config**: `config/mcp.json`

## 🚨 CRITICAL Git Workflow Rules

### Mandatory File Creation Workflow
**NEVER** create files remotely using GitHub MCP tools or API. **ALWAYS** follow this exact sequence:

1. **Create Locally**: Use `Write` tool to create files in local filesystem
2. **Stage**: `git add <file>` to stage changes
3. **Commit**: `git commit -m "message"` to commit locally
4. **Push**: `git push` to sync with remote

### Absolutely Forbidden Operations
❌ **NEVER** use `mcp__multi-mcp__github_create_or_update_file` for new files  
❌ **NEVER** create files directly on remote repository  
❌ **NEVER** bypass local Git workflow  
❌ **NEVER** create divergence between local and remote  

### Why This Matters
- **Repository Integrity**: Maintains consistent Git history
- **Collaboration**: Ensures all changes go through proper review process
- **Conflict Prevention**: Avoids merge conflicts and divergence
- **Workflow Compliance**: Follows standard Git practices

### Emergency Recovery from Divergence
If divergence occurs:
1. `git stash` (save local changes)
2. `git pull` (sync with remote)
3. `git stash pop` (restore local changes)
4. Resolve conflicts and follow proper workflow

### Investigation Storage
- **Location**: `claude/{investigation_id}/` directory structure
- **Naming**: Use timestamp-based IDs for unique identification
- **Example**: `claude/250627114051/investigation-file.md`

### File Organization
- **Investigations**: Store in `claude/{id}/` directories
- **Documentation**: Keep in root or `docs/` as appropriate
- **Configurations**: Use existing `examples/` structure
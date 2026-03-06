# Multi-MCP Copilot Instructions

## General guidelines (copy-friendly)

- **Response style**: End every reply with a concise summary covering completed work and next steps or current status.
- **Editing**: Keep indentation, formatting, and ASCII-only text unless non-ASCII already exists and is justified.
- **Change tracking**: Document structural, dependency, and workflow updates here; perform work on feature branches rather than directly on `main`.
- **Workflow vigilance**: If CI/CD or automation files change, monitor subsequent runs and surface failures quickly.
- **Branch etiquette**: Maintain feature branches per change; never revert user edits unless explicitly requested.
- **UI baseline**: Display the running build/version near the primary title (pulling from an env-driven constant such as `VITE_APP_VERSION`) and include a footer with `© {currentYear} Tekgnosis Pty Ltd`, computing the year at runtime so it stays current.
- **Docker build args**: Plumb an `APP_VERSION` build arg/ENV through container builds so the frontend/banner and metadata stay synchronized with release tags.
- **Runtime parity**: When merging frontend rewrites, ensure Dockerfile entrypoints, runtime scripts, and dependency sets are updated in the same change so published images launch the new stack (no legacy Mesop fallbacks).
- **Local image verification**: After any change that touches runtime code, Docker assets, or API endpoints, build the local image (`docker compose build mcp-multi`) and recreate the stack to validate end-to-end behavior before handing work back.

## Release & versioning

- **Semantic-release**: Automated releases run from `.github/workflows/release.yml`, using Conventional Commits to calculate the next SemVer version (starting at `v1.0.0`).
- **Release config**: `.releaserc.json` wires `@semantic-release/exec` to invoke `scripts/update_version.py <version>` so `pyproject.toml` (and `frontend/package.json` when present) stay in sync before the git/changelog plugins commit the artifacts.
- **Artifacts**: Successful releases push tags, changelog entries, GitHub releases, and GHCR images tagged with both the computed SemVer and `latest` via the release workflow.
- **Commit hygiene**: Format commit messages as Conventional Commits (`feat`, `fix`, `chore`, etc.) to ensure correct version bumps.

## Project Snapshot
- Multi-MCP exposes a single MCP server that multiplexes multiple backends; core runtime lives under `src/multimcp/`.
- CLI entry `main.py` accepts `--transport stdio|http`, `--config`, `--host`, `--port`, `--log-level` and instantiates `MultiMCP` with those settings (default transport is `http`).

## Architecture & Responsibilities
- `multi_mcp.MultiMCP` loads JSON config (default `./examples/config/mcp.json` via CLI, `./mcp.json` via `MCPSettings`), wires Rich logging, builds an `MCPClientManager`, then serves either stdio or an HTTP management API via `start_stdio_server` / `start_http_server` helpers.
- `mcp_client.MCPClientManager` tracks clients in `ManagedClient` wrappers, each with its own `AsyncExitStack`; use `add_client`, `remove_client`, `update_clients`, and `attach_existing` when mutating the pool so contexts close cleanly.
- `mcp_proxy.MCPProxyServer` subclasses `mcp.server.Server`, registers request/notification handlers, reconciles aggregated capabilities, and now accumulates per-server telemetry via `ServerStats` for the HTTP dashboard endpoints.

## Transport Modes & Dynamic API
- STDIO mode uses `mcp.server.stdio.stdio_server()` and is intended for pipe-based agents.
- HTTP mode exposes Starlette endpoints backed by **Streamable HTTP** (`StreamableHTTPSessionManager`) at `GET|POST|DELETE /mcp` (MCP 2025-11-25 spec) and a **legacy SSE** fallback at `GET /sse`, plus management API under `/api/*`: `GET /api/health`, `GET|PUT /api/config`, `GET|POST /api/servers`, `GET|DELETE /api/servers/{name}`, `GET /api/stats`, and `GET /api/tools`. Config updates call `MultiMCP.apply_config`, which diffs the running set, hot-swaps clients, and persists back to the path specified by `--config`.
- The `StreamableHTTPSessionManager` lifecycle is managed via a Starlette `lifespan` context; the watcher and uvicorn run concurrently in `anyio.create_task_group()`.
- **Config file watching**: `MultiMCP._watch_config()` uses `watchfiles.awatch` to watch the config JSON path; any change triggers `apply_config(..., persist=False)` for zero-downtime hot-reload.

## Tool & Capability Namespacing
- Tools are renamed via `_make_key(server_name, tool_name)` (e.g. `weather_get_forecast`) before exposure; always reference namespaced names when calling `call_tool`.
- `_initialize_tools_for_client` stores `ToolMapping` objects keyed by the namespaced name; updating tool logic requires touching both `tool_to_server` and the returned `Tool` clones.
- Prompt/resource lookups are capability-aware; check `self.capabilities[name]` before calling list/get APIs to avoid "Method not found" errors.

## Client Lifecycle & Configuration
- `create_clients` accepts `mcpServers` entries with either `command`+`args` (stdio) or `url` (SSE backend); env vars merge with `os.environ` and support encoding overrides from `langchain_mcp_adapters` defaults.
- Use `update_clients` or `apply_config` to hot-reload servers; these helpers reconcile additions, removals, and changes, keeping telemetry maps in sync and rewriting the config file (path from `--config`) when `persist=True`.
- Config load failures are logged and abort startup; when adding new config fields update `MCPSettings` in `multi_mcp.py` and mirror behavior in `load_mcp_config`.

## Logging & Error Handling
- Use project logger namespace via `get_logger("Component")`; emojis (`✅/⚠️/❌`) appear in existing logs, keep the convention for quick scanability.
- The proxy degrades gracefully: missing tools/prompts/resources return `ServerResult(... isError=True)` with explanatory text; follow the same pattern for new handlers.

- Preferred run: `uv run main.py --transport http --config ./examples/config/mcp.json`; `make run` wraps `uv run main.py` (defaults to HTTP transport on `127.0.0.1:8080`).
- Targeted tests use `make test-proxy` / `make test-e2e` / `make test-lifecycle`.
- Docker helpers: `make docker-build` builds the uv-based image, `make docker-run` maps port `8080`.
- Compose defaults to `ghcr.io/tekgnosis-net/multi-mcp:${IMAGE_TAG:-latest}`; set `IMAGE_TAG` before `docker compose up` to test a specific release.

## Testing Patterns
- Async tests rely on `pytest-asyncio`; see `tests/proxy_test.py` for in-memory servers via `mcp.shared.memory.create_connected_server_and_client_session`.
- Tool namespace assertions expect underscore separators; replicate `_make_key` usage in new tests to avoid coupling to internal format.
- Tests often inspect `CallToolResult` content arrays; when stubbing clients, return `[]` for success to match current expectations.

## Extensibility Notes
- New request/notification types should be registered in `_register_request_handlers`; keep capability checks and logging consistent.
- When adding clients dynamically, use `apply_config` so both `MCPClientManager` and `MCPProxyServer` keep telemetry in sync; direct mutation of `client_manager.clients` is obsolete.
- HTTP endpoints live in `MultiMCP.start_http_server`; extend them here when exposing new management capabilities (e.g., per-tool stats) and remember to persist config changes when appropriate.

Let me know if any part of this guide is unclear or if other workflows should be documented.

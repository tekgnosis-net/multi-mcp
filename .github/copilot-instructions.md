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

## Release & versioning

- **Semantic-release**: Automated releases run from `.github/workflows/release.yml`, using Conventional Commits to calculate the next SemVer version (starting at `v1.0.0`).
- **Release config**: `.releaserc.json` wires `@semantic-release/exec` to invoke `scripts/update_version.py <version>` so `pyproject.toml` (and `frontend/package.json` when present) stay in sync before the git/changelog plugins commit the artifacts.
- **Artifacts**: Successful releases push tags, changelog entries, GitHub releases, and GHCR images tagged with both the computed SemVer and `latest` via the release workflow.
- **Commit hygiene**: Format commit messages as Conventional Commits (`feat`, `fix`, `chore`, etc.) to ensure correct version bumps.

## Project Snapshot
- Multi-MCP exposes a single MCP server that multiplexes multiple backends; core runtime lives under `src/multimcp/`.
- CLI entry `main.py` accepts `--transport stdio|sse`, `--config`, `--host`, `--port`, `--log-level` and instantiates `MultiMCP` with those settings.

## Architecture & Responsibilities
- `multi_mcp.MultiMCP` loads JSON config (default `./examples/config/mcp.json`), wires Rich logging, builds an `MCPClientManager`, then starts stdio or SSE transport via `_start_*` helpers.
- `mcp_client.MCPClientManager` owns a single `AsyncExitStack`; always create/close clients through this manager so sessions are tracked and closed via `close()`.
- `mcp_proxy.MCPProxyServer` subclasses `mcp.server.Server`, registers request/notification handlers, and reconciles aggregated capabilities before relaying calls.

## Transport Modes & Dynamic API
- STDIO mode uses `mcp.server.stdio.stdio_server()` and is intended for pipe-based agents; SSE mode mounts a Starlette app with `/sse` plus `/mcp_servers`, `/mcp_servers/{name}`, `/mcp_tools` management endpoints.
- Runtime add/remove of servers only works in SSE mode because handlers call `register_client`/`unregister_client` on `self.proxy.client_manager`.

## Tool & Capability Namespacing
- Tools are renamed via `_make_key(server_name, tool_name)` (e.g. `weather_get_forecast`) before exposure; always reference namespaced names when calling `call_tool`.
- `_initialize_tools_for_client` stores `ToolMapping` objects keyed by the namespaced name; updating tool logic requires touching both `tool_to_server` and the returned `Tool` clones.
- Prompt/resource lookups are capability-aware; check `self.capabilities[name]` before calling list/get APIs to avoid "Method not found" errors.

## Client Lifecycle & Configuration
- `create_clients` accepts `mcpServers` entries with either `command`+`args` (stdio) or `url` (SSE); env vars merge with `os.environ` and support encoding overrides from `langchain_mcp_adapters` defaults.
- Config load failures are logged and abort startup; when adding new config fields update `MCPSettings` in `multi_mcp.py` and mirror behavior in `load_mcp_config`.

## Logging & Error Handling
- Use project logger namespace via `get_logger("Component")`; emojis (`✅/⚠️/❌`) appear in existing logs, keep the convention for quick scanability.
- The proxy degrades gracefully: missing tools/prompts/resources return `ServerResult(... isError=True)` with explanatory text; follow the same pattern for new handlers.

## Local Workflows
- Preferred run: `uv run main.py --transport sse --config ./examples/config/mcp.json`; `make run` wraps the default stdio launch.
- Targeted tests use `make test-proxy` / `make test-e2e` / `make test-lifecycle`; `make all-test` currently references a missing `test-k` target—run individual make targets or `pytest` directly when you need the full suite.
- Docker helpers: `make docker-build` builds the uv-based image, `make docker-run` maps port `8080`.
- Compose defaults to `ghcr.io/tekgnosis-net/multi-mcp:${IMAGE_TAG:-latest}`; set `IMAGE_TAG` before `docker compose up` to test a specific release.

## Testing Patterns
- Async tests rely on `pytest-asyncio`; see `tests/proxy_test.py` for in-memory servers via `mcp.shared.memory.create_connected_server_and_client_session`.
- Tool namespace assertions expect underscore separators; replicate `_make_key` usage in new tests to avoid coupling to internal format.
- Tests often inspect `CallToolResult` content arrays; when stubbing clients, return `[]` for success to match current expectations.

## Extensibility Notes
- New request/notification types should be registered in `_register_request_handlers`; keep capability checks and logging consistent.
- When adding clients dynamically, ensure `register_client` populates all maps; remember `unregister_client` filters existing dicts by client identity.
- SSE handler in `MultiMCP.start_sse_server` uses `SseServerTransport("/messages/")`; align with that path if you add reverse proxies or docs.

Let me know if any part of this guide is unclear or if other workflows should be documented.

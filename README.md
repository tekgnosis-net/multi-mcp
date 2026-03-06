
# **Multi MCP**

A flexible and dynamic **Multi-MCP** Proxy Server that acts as a single MCP server while connecting
to and routing between multiple backend MCP servers. Agents connect via **Streamable HTTP** (MCP 2025-11-25 spec) or legacy **SSE**; a RESTful control plane exposes live configuration and telemetry. Config changes are hot-reloaded automatically — no restarts needed.

<p align="center">
  <img src="assets/multi-mcp-diagram.png" alt="Multi-MCP Server Architecture" width="300"/>
</p>

## 🚀 Features

- ✅ **Streamable HTTP** transport (`/mcp`) — MCP 2025-11-25 spec with resumable SSE streams
- ✅ Legacy **SSE** transport (`/sse`) for backward-compatible clients
- ✅ **STDIO** transport for pipe-based agents
- ✅ Connects to backend MCP servers running in either `STDIO` or `SSE` mode
- ✅ Proxies tools, prompts, and resources from multiple backend servers
- ✅ Automatically namespaces tools as `server_tool` to avoid conflicts
- ✅ Dynamically **add/remove MCP servers at runtime** via HTTP API — no restart required
- ✅ **Config hot-reload**: changes to `mcp.json` are auto-applied via `watchfiles`
- ✅ Deployable on Kubernetes — a single port accesses all connected MCP servers

## 📦 Installation

```bash
git clone https://github.com/tekgnosis-net/multi-mcp.git
cd multi-mcp

# Install using uv (recommended)
uv venv
uv pip install -r requirements.txt
```

## 🖥️ Running Locally

### HTTP mode (default)

Starts the Streamable HTTP server on `127.0.0.1:8080` with the React dashboard and management API.

```bash
uv run main.py --transport http
# or with explicit options:
uv run main.py --transport http --host 0.0.0.0 --port 8096 --config ./config/mcp.json
```

### STDIO mode

For pipe-based agents and CLI integrations.

```bash
uv run main.py --transport stdio
```

`make run` is a shorthand for `uv run main.py` (defaults to HTTP on `127.0.0.1:8080`).

## ⚙️ Configuration

The proxy is initialised from a JSON file (default: `./mcp.json`):

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["./tools/get_weather.py"]
    },
    "calculator": {
      "command": "python",
      "args": ["./tools/calculator.py"]
    },
    "remote": {
      "url": "http://127.0.0.1:9080/sse"
    }
  }
}
```

Tool names are automatically namespaced as `server_tool` to avoid conflicts (e.g. `calculator_add`, `weather_get_forecast`). More examples are in [`examples/config/`](./examples/config/).

### Config hot-reload

`mcp.json` is watched at runtime using `watchfiles`. Any save to the file automatically adds, removes, or updates the affected backend servers — the change is applied within seconds with no process restart.

## 🔌 MCP Client Endpoints

Launch with `--transport http` (the default in Docker):

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `GET \| POST \| DELETE /mcp` | **Streamable HTTP** (MCP 2025-11-25) | Primary MCP endpoint — stateful & stateless sessions, resumable streams |
| `GET /sse` | Legacy SSE | Backward-compatible SSE for older clients |

## 🔄 Dynamic Server Management (HTTP API)

Add, remove, or inspect backend servers at runtime without restarting the proxy. Changes are persisted back to the config file automatically.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/servers` | List active MCP servers with telemetry |
| `POST` | `/api/servers` | Add `mcpServers` entries |
| `GET` | `/api/servers/{name}` | Inspect a single server |
| `DELETE` | `/api/servers/{name}` | Remove a server by name |
| `GET` | `/api/config` | Fetch the current configuration |
| `PUT` | `/api/config` | Replace the configuration and hot-reload |
| `GET` | `/api/stats` | Per-server stats (tool counts, invocations, errors) |
| `GET` | `/api/tools` | List tools grouped by server |
| `GET` | `/api/health` | Liveness probe |

### Example: add a server at runtime

```bash
curl -X POST http://localhost:8096/api/servers \
  -H "Content-Type: application/json" \
  -d '{"mcpServers": {"unit_converter": {"command": "python", "args": ["./tools/unit_convertor.py"]}}}'
```

## 🖼️ React Dashboard

A React/Vite frontend lives under `frontend/` and is served from `/` when running in HTTP mode. It gives a visual overview of connected servers, tool counts, invocation stats, and a live JSON config editor.

To run the dashboard in development:

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` calls to `http://127.0.0.1:8080`, so start the backend first with `uv run main.py --transport http`.

## 🐳 Docker

Pre-built images are published to GHCR on every release:

```bash
docker pull ghcr.io/tekgnosis-net/multi-mcp:latest
docker run -p 8096:8096 ghcr.io/tekgnosis-net/multi-mcp:latest
```

### Docker Compose (recommended)

`docker-compose.yml` pulls the latest GHCR image and mounts your local `config/` directory so `mcp.json` edits hot-reload inside the container:

```bash
docker compose up -d
# pin a specific version:
IMAGE_TAG=1.2.0 docker compose up -d
```

The config volume is mounted at `/config` and the container reads `CONFIG_FILE=/config/mcp.json` by default, so any local edit to `config/mcp.json` is picked up automatically.

### Build locally

```bash
make docker-build   # builds multi-mcp:local
make docker-run     # runs on port 8096
```

## ☸️ Kubernetes

Deploy the proxy in a Kubernetes cluster using the provided manifests.

### Run with [Kind](https://kind.sigs.k8s.io/)

```bash
kind create cluster --name multi-mcp-test
kind load docker-image multi-mcp --name multi-mcp-test
kubectl apply -f examples/k8s/multi-mcp.yaml
```

The manifest exposes the HTTP API via a NodePort (30080 by default):

```bash
curl http://<kind-node-ip>:30080/api/health
```

## 🔗 Connecting MCP Clients

Once the proxy is running, any MCP-compatible client can connect to it. For a LangGraph agent example using `langchain_mcp_adapters`, see [`examples/connect_langgraph_client.py`](examples/connect_langgraph_client.py).

Required `.env` for the example:

```env
MODEL_NAME=<your-model-name>
BASE_URL=<https://your-openai-base-url>
OPENAI_API_KEY=<your-api-key>
```

## 💡 Inspiration

- [`mcp-proxy`](https://github.com/sparfenyuk/mcp-proxy) by @sparfenyuk
- [`fastmcp`](https://github.com/jlowin/fastmcp) by @jlowin


# ── Stage 1: build frontend ──────────────────────────────────────────────────
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

# Install dependencies first (layer-cached unless package.json changes)
COPY frontend/package.json ./
RUN npm install --no-audit --progress=false

# Build the Vite app
COPY frontend/ ./
RUN npm run build


# ── Stage 2: build Python venv ───────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS python-builder

WORKDIR /app

# Install Python deps into an isolated venv (layer-cached unless requirements change)
COPY requirements.txt ./
RUN uv venv /app/.venv \
    && uv pip install --no-cache -r requirements.txt


# ── Stage 3: runtime image ───────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/kfirtoledo/multi-mcp"

WORKDIR /app

# Install Node.js (runtime requirement for npx-based MCP servers like searxng, sequentialthinking)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built venv from builder stage
COPY --from=python-builder /app/.venv /app/.venv

# Copy the pre-built frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy application source (benefits from layer cache because venv is already copied)
COPY main.py ./
COPY src/ ./src/
COPY config/mcp.json /app/mcp.json

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=/app

# Runtime defaults (override via docker-compose / docker run -e)
ENV TRANSPORT_TYPE=http
ENV CONFIG_FILE=mcp.json
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8096
ENV LOG_LEVEL=INFO

CMD ["sh", "-c", "exec python main.py --transport $TRANSPORT_TYPE --config $CONFIG_FILE --host $MCP_HOST --port $MCP_PORT --log-level $LOG_LEVEL"]

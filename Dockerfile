FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.version="${APP_VERSION}"

# Install Node.js for MCP servers
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN uv venv \
    && uv pip install -r requirements.txt

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=/app

# Copy production config file
COPY ./config/mcp.json /app/mcp.json

# Setup environment variable for docker compose
ENV TRANSPORT_TYPE=sse
ENV CONFIG_FILE=mcp.json
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8096
ENV LOG_LEVEL=INFO
# Start app

#ENTRYPOINT ["python", "main.py"]
CMD python main.py --transport $TRANSPORT_TYPE --config $CONFIG_FILE --host $MCP_HOST --port $MCP_PORT --log-level $LOG_LEVEL

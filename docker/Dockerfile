# Multi-stage Dockerfile for GraphMerge MCP Server
# Reference implementation of arXiv:2610.30074

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[languages]"

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src
COPY pyproject.toml README.md ./

ENV PYTHONUNBUFFERED=1

# Defaults to running the GraphMerge MCP stdio server
ENTRYPOINT ["python3", "-m", "graphmerge.mcp_server"]

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Railway provides PORT env var, default to 8000
ENV PORT=8000
ENV HOST=0.0.0.0

# MCP_API_KEY must be set at runtime (Railway env vars / docker run -e)
# Server will refuse to start if MCP_API_KEY is not set.

EXPOSE 8000

# Run MCP server with Streamable HTTP transport
CMD uvicorn src.mcp_server.server:app --host $HOST --port $PORT

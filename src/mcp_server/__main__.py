"""MCP Server package entry point.

This module allows running the MCP server as:
    python -m src.mcp_server              # Starts HTTP server on port 8000

For production (Railway, Docker, etc.):
    uvicorn src.mcp_server.server:app --host 0.0.0.0 --port $PORT
"""

from .server import main

if __name__ == "__main__":
    main()

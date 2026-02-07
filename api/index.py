"""Vercel serverless entrypoint for the MCP server.

Vercel's Python runtime expects an ASGI `app` object in the handler file.
This module re-exports the ASGI app (with API key middleware) from the
main server module so Vercel can serve it as a serverless function.

The FastMCP instance is created with `stateless_http=True`, which means
every request is independent — no session persistence is needed. This
makes it fully compatible with Vercel's serverless execution model.

Environment variables required (set in Vercel dashboard):
    - DATABASE_URL: Neon PostgreSQL connection string
    - MCP_API_KEY: Bearer token for authenticating requests
"""

from src.mcp_server.server import app

# Vercel picks up `app` automatically as the ASGI handler.

"""MCP server implementation for query-agent.

This module implements the main MCP server that exposes 10 tools for task management
and SQL operations. The server uses Streamable HTTP transport for remote deployment.

Architecture:
    - Server uses FastMCP (high-level API) with Streamable HTTP transport
    - Low-level tool handlers registered on FastMCP._mcp_server for full control
    - Manages database connection pool lifecycle via lifespan
    - Registers 10 tools for task management, batch operations, and SQL queries
    - Deployed as ASGI app (Vercel serverless, Docker, or uvicorn locally)

Security:
    - All tools enforce user_id filtering per SECURITY.md
    - SQL queries are parameterized to prevent injection
    - execute_sql_query is SELECT-only (read-only)
"""

import os
import json
import sys
import hmac
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from . import database
from .tools import task_tools, batch_tools, sql_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("query-agent-mcp")


# ---------------------------------------------------------------------------
# API Key Authentication Middleware
# ---------------------------------------------------------------------------

# Load API key at module level — server refuses to start without it.
_MCP_API_KEY = os.environ.get("MCP_API_KEY", "")


class APIKeyMiddleware:
    """Starlette ASGI middleware that enforces Bearer token authentication.

    Checks every request to the MCP endpoint for a valid
    ``Authorization: Bearer <MCP_API_KEY>`` header.  Uses constant-time
    comparison (``hmac.compare_digest``) to prevent timing attacks.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope, receive)
            auth_header = request.headers.get("authorization", "")

            if not auth_header.startswith("Bearer "):
                response = JSONResponse(
                    {"error": "Missing or malformed Authorization header"},
                    status_code=401,
                )
                logger.warning(
                    "AUTH FAILED: Missing Bearer token from %s",
                    request.client.host if request.client else "unknown",
                )
                await response(scope, receive, send)
                return

            token = auth_header[7:]  # Strip "Bearer "

            if not hmac.compare_digest(token, _MCP_API_KEY):
                response = JSONResponse(
                    {"error": "Invalid API key"},
                    status_code=401,
                )
                logger.warning(
                    "AUTH FAILED: Invalid API key from %s",
                    request.client.host if request.client else "unknown",
                )
                await response(scope, receive, send)
                return

        # Auth passed — forward to the MCP handler
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Lifespan: database pool init / cleanup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server startup and shutdown lifecycle.

    Initializes the database connection pool on startup and ensures
    graceful cleanup on shutdown.

    Yields:
        dict: Lifespan context containing the database pool
    """
    pool = await database.get_db_pool()
    logger.info("Database connection pool initialized")

    try:
        yield {"pool": pool}
    finally:
        await database.close_db_pool()
        logger.info("Database connection pool closed")


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "query-agent-mcp",
    lifespan=server_lifespan,
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
)

# Get the underlying low-level server for registering handlers
server = mcp._mcp_server


# ---------------------------------------------------------------------------
# Tool Definitions (registered on the low-level server)
# ---------------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools.

    Returns the complete set of 10 tools:
    - 6 task management tools
    - 2 batch operation tools
    - 2 SQL query tools
    """
    return [
        # ── Task Management Tools ──────────────────────────────────
        types.Tool(
            name="create_task",
            description="Create a new task for a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID who owns the task"},
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description (optional)"},
                    "due_date": {"type": "string", "format": "date-time", "description": "Due date (ISO 8601, optional)"},
                },
                "required": ["user_id", "title"],
            },
        ),
        types.Tool(
            name="list_tasks",
            description="List all tasks for a user with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Filter by status (optional)",
                    },
                },
                "required": ["user_id"],
            },
        ),
        types.Tool(
            name="update_task",
            description="Update an existing task",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (for authorization)"},
                    "task_id": {"type": "integer", "description": "Task ID to update"},
                    "title": {"type": "string", "description": "New title (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "New status (optional)",
                    },
                    "due_date": {"type": "string", "format": "date-time", "description": "New due date (optional)"},
                },
                "required": ["user_id", "task_id"],
            },
        ),
        types.Tool(
            name="delete_task",
            description="Delete a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (for authorization)"},
                    "task_id": {"type": "integer", "description": "Task ID to delete"},
                },
                "required": ["user_id", "task_id"],
            },
        ),
        types.Tool(
            name="get_task_details",
            description="Get detailed information about a specific task",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (for authorization)"},
                    "task_id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["user_id", "task_id"],
            },
        ),
        types.Tool(
            name="search_tasks_by_keyword",
            description="Search tasks by keyword in title or description",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "keyword": {"type": "string", "description": "Search keyword"},
                },
                "required": ["user_id", "keyword"],
            },
        ),
        # ── Batch Operation Tools ──────────────────────────────────
        types.Tool(
            name="batch_delete_tasks",
            description="Delete multiple tasks at once (max 100)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (for authorization)"},
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "maxItems": 100,
                        "description": "Array of task IDs to delete",
                    },
                },
                "required": ["user_id", "task_ids"],
            },
        ),
        types.Tool(
            name="batch_update_tasks",
            description="Update multiple tasks at once (max 100)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (for authorization)"},
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "maxItems": 100,
                        "description": "Array of task IDs to update",
                    },
                    "updates": {
                        "type": "object",
                        "description": "Fields to update on all tasks",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                            }
                        },
                    },
                },
                "required": ["user_id", "task_ids", "updates"],
            },
        ),
        # ── SQL Query Tools ────────────────────────────────────────
        types.Tool(
            name="generate_sql_query",
            description="Generate SQL query from natural language (returns SQL string, doesn't execute)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (for query context)"},
                    "natural_language_query": {
                        "type": "string",
                        "description": "Natural language description of desired query",
                    },
                },
                "required": ["user_id", "natural_language_query"],
            },
        ),
        types.Tool(
            name="execute_sql_query",
            description="Execute a SELECT-only SQL query (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (enforces user_id filtering)"},
                    "sql_query": {"type": "string", "description": "SELECT query to execute"},
                },
                "required": ["user_id", "sql_query"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool Router
# ---------------------------------------------------------------------------

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any],
) -> list[types.TextContent]:
    """Route tool calls to the appropriate handler function."""

    # Get database pool from lifespan context
    ctx = server.request_context
    pool = ctx.lifespan_context.get("pool")
    if not pool:
        return [types.TextContent(type="text", text=json.dumps({"error": "Database pool not initialized"}))]

    try:
        # ── Task Management ────────────────────────────────────
        if name == "create_task":
            result = await task_tools.create_task(
                pool,
                user_id=arguments["user_id"],
                title=arguments["title"],
                description=arguments.get("description", ""),
                due_date=arguments.get("due_date"),
            )
        elif name == "list_tasks":
            result = await task_tools.list_tasks(
                pool,
                user_id=arguments["user_id"],
                status=arguments.get("status"),
            )
        elif name == "update_task":
            result = await task_tools.update_task(
                pool,
                user_id=arguments["user_id"],
                task_id=arguments["task_id"],
                title=arguments.get("title"),
                description=arguments.get("description"),
                status=arguments.get("status"),
                due_date=arguments.get("due_date"),
            )
        elif name == "delete_task":
            result = await task_tools.delete_task(
                pool,
                user_id=arguments["user_id"],
                task_id=arguments["task_id"],
            )
        elif name == "get_task_details":
            result = await task_tools.get_task_details(
                pool,
                user_id=arguments["user_id"],
                task_id=arguments["task_id"],
            )
        elif name == "search_tasks_by_keyword":
            result = await task_tools.search_tasks_by_keyword(
                pool,
                user_id=arguments["user_id"],
                keyword=arguments["keyword"],
            )
        # ── Batch Operations ───────────────────────────────────
        elif name == "batch_delete_tasks":
            result = await batch_tools.batch_delete_tasks(
                pool,
                user_id=arguments["user_id"],
                task_ids=arguments.get("task_ids", []),
            )
        elif name == "batch_update_tasks":
            updates = arguments.get("updates", {})
            result = await batch_tools.batch_update_tasks(
                pool,
                user_id=arguments["user_id"],
                task_ids=arguments.get("task_ids", []),
                status=updates.get("status"),
            )
        # ── SQL Operations ─────────────────────────────────────
        elif name == "generate_sql_query":
            result = await sql_tools.generate_sql_query(
                pool,
                user_id=arguments["user_id"],
                question=arguments["natural_language_query"],
            )
        elif name == "execute_sql_query":
            result = await sql_tools.execute_sql_query(
                pool,
                user_id=arguments["user_id"],
                query=arguments["sql_query"],
            )
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, default=str))]

    except Exception as e:
        logger.error(f"Tool execution failed: {name} - {e}")
        return [types.TextContent(type="text", text=json.dumps({"error": "Tool execution failed. Check server logs for details."}))]


# ---------------------------------------------------------------------------
# ASGI Application (Streamable HTTP)
# ---------------------------------------------------------------------------

# Starlette ASGI app served by uvicorn — endpoint: /mcp
# Wrapped with API key authentication middleware
_raw_app = mcp.streamable_http_app()
app = APIKeyMiddleware(_raw_app)


def main() -> None:
    """Entry point for running the server directly.

    Usage:
        python -m src.mcp_server

    For production:
        Vercel:  vercel deploy (uses api/index.py)
        Docker:  uvicorn src.mcp_server.server:app --host 0.0.0.0 --port $PORT
    """
    import uvicorn

    # --- Startup guard: refuse to run without API key ---
    if not _MCP_API_KEY:
        logger.critical("MCP_API_KEY environment variable is not set. Aborting.")
        sys.exit(1)

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"Starting MCP server on {host}:{port}")
    logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
    logger.info("API key authentication: ENABLED")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

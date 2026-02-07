# MCP Server Setup Guide (Python)

> **Context file for creating `query-agent-mcp` repository**
> 
> This document provides the complete setup for extracting all agent tools into a standalone Python MCP server.

## Project Structure

```
query-agent-mcp/          # New separate repo (Python)
├── src/
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py           # MCP server entry point
│   │   ├── database.py         # Neon DB connection
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── task_tools.py   # CRUD operations (6 tools)
│   │       ├── batch_tools.py  # Batch operations (2 tools)
│   │       └── sql_tools.py    # SQL operations (2 tools)
├── .env
├── .env.example
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Tech Stack

```toml
[project]
name = "query-agent-mcp"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "mcp>=1.0.0",              # MCP Python SDK
    "asyncpg>=0.29.0",         # Async PostgreSQL driver
    "python-dotenv>=1.0.0",    # Environment variables
]
```

## Tools to Migrate (10 total)

From `backend/app/agent/tools.py`:

### Task Management (6 tools)
1. **create_task** - Create new task with optional due_date and created_by tracking
2. **list_tasks** - List all tasks with status filter (sorted oldest to newest)
3. **update_task** - Update task (title, description, status, due_date) - all fields optional
4. **delete_task** - Delete single task by ID
5. **get_task_details** - Get detailed task info including created_by
6. **search_tasks_by_keyword** - Fuzzy search by title/description with similarity matching

### Batch Operations (2 tools)
7. **batch_delete_tasks** - Delete up to 100 tasks with comma-separated IDs
8. **batch_update_tasks** - Update multiple tasks (title, description, status, due_date)

### SQL Operations (2 tools)
9. **generate_sql_query** - Generate SQL from natural language questions
10. **execute_sql_query** - Execute SELECT queries with user_id filtering and safety checks

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Todos table
CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(1000) DEFAULT NULL,
    status VARCHAR DEFAULT 'pending',
    due_date TIMESTAMP DEFAULT NULL,
    user_id INTEGER REFERENCES users(id),
    created_by VARCHAR(100) DEFAULT NULL,  -- "task created by 'username'"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Conversation history table
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Environment Variables

Create `.env`:

```bash
# Neon Database (same as main agent)
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# MCP Server
MCP_SERVER_NAME=neon-task-server
MCP_SERVER_VERSION=1.0.0
```

## MCP Server Implementation

### 1. Database Connection (`src/mcp_server/database.py`)

```python
"""Database connection using asyncpg for Neon PostgreSQL."""
import os
import asyncpg
from typing import Optional

_pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not set")
        
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=10,
        )
    return _pool

async def close_db_pool():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

### 2. Tool Context

```python
"""User context passed to all tools."""
from dataclasses import dataclass
import asyncpg

@dataclass
class ToolContext:
    """Context for tool execution."""
    user_id: int
    db_pool: asyncpg.Pool
```

### 3. Task Management Tools (`src/mcp_server/tools/task_tools.py`)

```python
"""Task CRUD operations - 6 tools."""
from datetime import datetime
from typing import Optional
from mcp.server import Tool
from mcp.types import TextContent
import asyncpg

async def create_task(
    context,
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
) -> dict:
    """Create a new task with automatic created_by tracking."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Parse due_date
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    async with pool.acquire() as conn:
        # Get username for created_by
        user = await conn.fetchrow(
            "SELECT username FROM users WHERE id = $1",
            user_id
        )
        username = user['username'] if user else 'unknown'
        created_by = f"task created by '{username}'"
        
        # Insert task
        task = await conn.fetchrow("""
            INSERT INTO todos (title, description, due_date, user_id, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, title, status, created_at, created_by
        """, title, description or None, parsed_due_date, user_id, created_by)
        
        return {
            "success": True,
            "task_id": task['id'],
            "message": f"✅ Created task #{task['id']}: '{title}'"
        }

async def list_tasks(
    context,
    status: str = "all",
) -> dict:
    """List all tasks (sorted oldest to newest)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        if status == "all":
            query = """
                SELECT id, title, status, due_date, created_at, created_by
                FROM todos 
                WHERE user_id = $1
                ORDER BY created_at ASC
            """
            tasks = await conn.fetch(query, user_id)
        else:
            query = """
                SELECT id, title, status, due_date, created_at, created_by
                FROM todos 
                WHERE user_id = $1 AND status = $2
                ORDER BY created_at ASC
            """
            tasks = await conn.fetch(query, user_id, status)
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [dict(t) for t in tasks]
        }

async def update_task(
    context,
    task_id: int,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> dict:
    """Update a single task (all fields optional)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Build dynamic update query
    updates = []
    params = []
    param_count = 1
    
    if title is not None:
        updates.append(f"title = ${param_count}")
        params.append(title)
        param_count += 1
    
    if status is not None:
        if status not in ["pending", "completed"]:
            return {"error": "❌ Invalid status. Use 'pending' or 'completed'"}
        updates.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1
    
    if description is not None:
        updates.append(f"description = ${param_count}")
        params.append(description)
        param_count += 1
    
    if due_date is not None:
        if due_date.lower() == "none":
            updates.append("due_date = NULL")
        else:
            try:
                parsed = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                updates.append(f"due_date = ${param_count}")
                params.append(parsed)
                param_count += 1
            except (ValueError, AttributeError):
                return {"error": "❌ Invalid due date format"}
    
    if not updates:
        return {"error": "❌ No updates specified"}
    
    updates.append("updated_at = NOW()")
    params.extend([task_id, user_id])
    
    async with pool.acquire() as conn:
        query = f"""
            UPDATE todos 
            SET {', '.join(updates)}
            WHERE id = ${param_count} AND user_id = ${param_count + 1}
            RETURNING id, title, status, updated_at
        """
        task = await conn.fetchrow(query, *params)
        
        if not task:
            return {"error": f"❌ Task #{task_id} not found"}
        
        return {
            "success": True,
            "task": dict(task),
            "message": f"✅ Updated task #{task_id}"
        }

async def delete_task(context, task_id: int) -> dict:
    """Delete a single task by ID."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        task = await conn.fetchrow("""
            DELETE FROM todos 
            WHERE id = $1 AND user_id = $2
            RETURNING id, title
        """, task_id, user_id)
        
        if not task:
            return {"error": f"❌ Task #{task_id} not found"}
        
        return {
            "success": True,
            "message": f"✅ Deleted task #{task['id']}: '{task['title']}'"
        }

async def get_task_details(context, task_id: int) -> dict:
    """Get detailed information about a task."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        task = await conn.fetchrow("""
            SELECT id, title, description, status, due_date, 
                   created_by, created_at, updated_at
            FROM todos 
            WHERE id = $1 AND user_id = $2
        """, task_id, user_id)
        
        if not task:
            return {"error": f"❌ Task #{task_id} not found"}
        
        return {
            "success": True,
            "task": dict(task)
        }

async def search_tasks_by_keyword(context, keyword: str) -> dict:
    """Search for tasks using fuzzy matching."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        # Use PostgreSQL similarity search
        tasks = await conn.fetch("""
            SELECT id, title, description, status, due_date, created_at
            FROM todos 
            WHERE user_id = $1 
            AND (title ILIKE $2 OR description ILIKE $2)
            ORDER BY created_at DESC
        """, user_id, f"%{keyword}%")
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [dict(t) for t in tasks],
            "keyword": keyword
        }
```

### 4. Batch Operations (`src/mcp_server/tools/batch_tools.py`)

```python
"""Batch operations - 2 tools."""
from datetime import datetime
from typing import Optional

async def batch_delete_tasks(context, task_ids: str) -> dict:
    """Delete multiple tasks by IDs (max 100)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Parse IDs
    try:
        ids = [int(id.strip()) for id in task_ids.split(",") if id.strip()]
    except ValueError:
        return {"error": "❌ Invalid task IDs format. Use '1,2,3'"}
    
    if not ids:
        return {"error": "❌ No task IDs provided"}
    
    if len(ids) > 100:
        return {"error": "❌ Maximum 100 tasks allowed"}
    
    async with pool.acquire() as conn:
        tasks = await conn.fetch("""
            DELETE FROM todos 
            WHERE id = ANY($1::int[]) AND user_id = $2
            RETURNING id, title
        """, ids, user_id)
        
        if not tasks:
            return {"error": f"❌ No tasks found with IDs: {task_ids}"}
        
        deleted_ids = [t['id'] for t in tasks]
        found_ids = set(deleted_ids)
        requested_ids = set(ids)
        missing_ids = requested_ids - found_ids
        
        message = f"✅ Successfully deleted {len(deleted_ids)} task(s): " + ", ".join([f"#{id}" for id in deleted_ids])
        
        if missing_ids:
            message += f"\n⚠️ Tasks not found: " + ", ".join([f"#{id}" for id in sorted(missing_ids)])
        
        return {
            "success": True,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "message": message
        }

async def batch_update_tasks(
    context,
    task_ids: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> dict:
    """Update multiple tasks with same values (max 100)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Parse IDs
    try:
        ids = [int(id.strip()) for id in task_ids.split(",") if id.strip()]
    except ValueError:
        return {"error": "❌ Invalid task IDs format. Use '1,2,3'"}
    
    if not ids:
        return {"error": "❌ No task IDs provided"}
    
    if len(ids) > 100:
        return {"error": "❌ Maximum 100 tasks allowed"}
    
    # Validate status
    if status and status not in ["pending", "completed"]:
        return {"error": "❌ Invalid status. Use 'pending' or 'completed'"}
    
    # Build dynamic update query
    updates = []
    params = []
    param_count = 1
    
    if title is not None:
        updates.append(f"title = ${param_count}")
        params.append(title)
        param_count += 1
    
    if status is not None:
        updates.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1
    
    if description is not None:
        updates.append(f"description = ${param_count}")
        params.append(description)
        param_count += 1
    
    if due_date is not None:
        if due_date.lower() == "none":
            updates.append("due_date = NULL")
        else:
            try:
                parsed = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                updates.append(f"due_date = ${param_count}")
                params.append(parsed)
                param_count += 1
            except (ValueError, AttributeError):
                return {"error": "❌ Invalid due date format"}
    
    if not updates:
        return {"error": "❌ No updates specified"}
    
    updates.append("updated_at = NOW()")
    params.extend([ids, user_id])
    
    async with pool.acquire() as conn:
        query = f"""
            UPDATE todos 
            SET {', '.join(updates)}
            WHERE id = ANY(${param_count}::int[]) AND user_id = ${param_count + 1}
            RETURNING id, title, status
        """
        tasks = await conn.fetch(query, *params)
        
        if not tasks:
            return {"error": f"❌ No tasks found with IDs: {task_ids}"}
        
        updated_ids = [t['id'] for t in tasks]
        updates_made = []
        if title: updates_made.append(f"title → '{title}'")
        if status: updates_made.append(f"status → {status}")
        if description: updates_made.append("description updated")
        if due_date: updates_made.append("due date updated" if due_date.lower() != "none" else "due date removed")
        
        message = f"✅ Successfully updated {len(updated_ids)} task(s): " + ", ".join([f"#{id}" for id in updated_ids])
        message += f"\nChanges: {', '.join(updates_made)}"
        
        return {
            "success": True,
            "updated_count": len(updated_ids),
            "updated_ids": updated_ids,
            "message": message
        }
```

### 5. SQL Operations (`src/mcp_server/tools/sql_tools.py`)

```python
"""SQL query tools - 2 tools."""
import re

DATABASE_SCHEMA = """
users (id, username, email, created_at)
todos (id, title, description, status, due_date, user_id, created_by, created_at, updated_at)
"""

async def generate_sql_query(context, question: str) -> dict:
    """Generate SQL from natural language."""
    user_id = context["user_id"]
    
    # Common patterns
    patterns = {
        r"how many.*completed": f"SELECT COUNT(*) as completed_count FROM todos WHERE user_id = {user_id} AND status = 'completed'",
        r"how many.*pending": f"SELECT COUNT(*) as pending_count FROM todos WHERE user_id = {user_id} AND status = 'pending'",
        r"how many.*task": f"SELECT COUNT(*) as total_tasks FROM todos WHERE user_id = {user_id}",
        r"list.*task": f"SELECT id, title, status, created_at FROM todos WHERE user_id = {user_id} ORDER BY created_at DESC",
        r"task.*today": f"SELECT id, title, status FROM todos WHERE user_id = {user_id} AND DATE(created_at) = CURRENT_DATE",
        r"task.*week": f"SELECT id, title, created_at FROM todos WHERE user_id = {user_id} AND created_at >= CURRENT_DATE - INTERVAL '7 days'",
    }
    
    question_lower = question.lower()
    
    for pattern, query in patterns.items():
        if re.search(pattern, question_lower):
            return {
                "success": True,
                "query": query,
                "message": f"Generated SQL query:\n```sql\n{query}\n```\n\nUse execute_sql_query to run this."
            }
    
    return {
        "success": True,
        "message": f"Could not generate query for: '{question}'\n\nDatabase schema:\n{DATABASE_SCHEMA}\n\nTry questions like:\n- 'How many completed tasks do I have?'\n- 'List all tasks created this week'"
    }

async def execute_sql_query(context, query: str) -> dict:
    """Execute SELECT queries with safety checks."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Safety checks
    query_upper = query.upper().strip()
    
    if not query_upper.startswith("SELECT"):
        return {"error": "❌ Only SELECT queries are allowed"}
    
    if any(keyword in query_upper for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]):
        return {"error": "❌ Modification queries are not allowed"}
    
    if "user_id" not in query.lower():
        return {"error": "❌ Query must filter by user_id for security"}
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            
            if not rows:
                return {
                    "success": True,
                    "message": "Query executed successfully but returned no results."
                }
            
            # Format results
            lines = []
            if rows:
                # Header
                headers = list(rows[0].keys())
                lines.append(" | ".join(headers))
                lines.append("-" * (len(" | ".join(headers))))
                
                # Rows (limit to 50)
                for row in rows[:50]:
                    lines.append(" | ".join(str(v) for v in row.values()))
                
                if len(rows) > 50:
                    lines.append(f"\n... and {len(rows) - 50} more rows")
            
            return {
                "success": True,
                "row_count": len(rows),
                "results": "\n".join(lines)
            }
    
    except Exception as e:
        return {"error": f"❌ SQL Error: {str(e)}\n\nPlease check your query syntax."}
```

### 6. MCP Server Entry (`src/mcp_server/server.py`)

```python
"""MCP Server implementation."""
import asyncio
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

from .database import get_db_pool, close_db_pool
from .tools.task_tools import (
    create_task, list_tasks, update_task, delete_task,
    get_task_details, search_tasks_by_keyword
)
from .tools.batch_tools import batch_delete_tasks, batch_update_tasks
from .tools.sql_tools import generate_sql_query, execute_sql_query

load_dotenv()

# Define all 10 tools
TOOLS = {
    # Task Management (6 tools)
    "create_task": {
        "function": create_task,
        "description": "Create a new task with automatic created_by tracking",
        "parameters": {
            "title": {"type": "string", "description": "Task title", "required": True},
            "description": {"type": "string", "description": "Task description", "required": False},
            "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)", "required": False},
        }
    },
    "list_tasks": {
        "function": list_tasks,
        "description": "List all tasks (sorted oldest to newest)",
        "parameters": {
            "status": {"type": "string", "description": "Filter: 'all', 'pending', 'completed'", "required": False, "default": "all"},
        }
    },
    "update_task": {
        "function": update_task,
        "description": "Update a single task (all fields optional)",
        "parameters": {
            "task_id": {"type": "number", "description": "Task ID to update", "required": True},
            "title": {"type": "string", "description": "New title", "required": False},
            "status": {"type": "string", "description": "New status (pending/completed)", "required": False},
            "description": {"type": "string", "description": "New description", "required": False},
            "due_date": {"type": "string", "description": "New due date or 'none'", "required": False},
        }
    },
    "delete_task": {
        "function": delete_task,
        "description": "Delete a single task by ID",
        "parameters": {
            "task_id": {"type": "number", "description": "Task ID to delete", "required": True},
        }
    },
    "get_task_details": {
        "function": get_task_details,
        "description": "Get detailed information about a task",
        "parameters": {
            "task_id": {"type": "number", "description": "Task ID", "required": True},
        }
    },
    "search_tasks_by_keyword": {
        "function": search_tasks_by_keyword,
        "description": "Search for tasks using fuzzy matching",
        "parameters": {
            "keyword": {"type": "string", "description": "Search keyword", "required": True},
        }
    },
    
    # Batch Operations (2 tools)
    "batch_delete_tasks": {
        "function": batch_delete_tasks,
        "description": "Delete multiple tasks (max 100)",
        "parameters": {
            "task_ids": {"type": "string", "description": "Comma-separated IDs (e.g., '1,2,3')", "required": True},
        }
    },
    "batch_update_tasks": {
        "function": batch_update_tasks,
        "description": "Update multiple tasks with same values (max 100)",
        "parameters": {
            "task_ids": {"type": "string", "description": "Comma-separated IDs", "required": True},
            "title": {"type": "string", "description": "New title for all", "required": False},
            "status": {"type": "string", "description": "New status", "required": False},
            "description": {"type": "string", "description": "New description", "required": False},
            "due_date": {"type": "string", "description": "New due date or 'none'", "required": False},
        }
    },
    
    # SQL Operations (2 tools)
    "generate_sql_query": {
        "function": generate_sql_query,
        "description": "Generate SQL from natural language",
        "parameters": {
            "question": {"type": "string", "description": "Natural language question", "required": True},
        }
    },
    "execute_sql_query": {
        "function": execute_sql_query,
        "description": "Execute SELECT queries safely",
        "parameters": {
            "query": {"type": "string", "description": "SQL SELECT query", "required": True},
        }
    },
}

async def main():
    """Run MCP server."""
    server = Server("neon-task-server")
    pool = await get_db_pool()
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools."""
        return [
            Tool(
                name=name,
                description=spec["description"],
                inputSchema={
                    "type": "object",
                    "properties": spec["parameters"],
                    "required": [k for k, v in spec["parameters"].items() if v.get("required", False)]
                }
            )
            for name, spec in TOOLS.items()
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict, meta: dict = None) -> list[TextContent]:
        """Execute a tool."""
        if name not in TOOLS:
            raise ValueError(f"Unknown tool: {name}")
        
        # Extract user_id from metadata (passed by agent)
        user_id = meta.get("user_id", 1) if meta else 1
        
        # Build context
        context = {
            "user_id": user_id,
            "db_pool": pool
        }
        
        # Call tool function
        tool_spec = TOOLS[name]
        result = await tool_spec["function"](context, **arguments)
        
        # Return result as text
        import json
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
    
    await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())
```

### 7. Project Configuration (`pyproject.toml`)

```toml
[project]
name = "query-agent-mcp"
version = "1.0.0"
description = "MCP server for Neon task management"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "asyncpg>=0.29.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
query-agent-mcp = "mcp_server.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  createTaskTool, 
  listTasksTool, 
  updateTaskTool, 
  deleteTaskTool,
  getTaskDetailsTool,
  searchTasksByKeywordTool
} from './tools/task-tools.js';
import { batchDeleteTasksTool, batchUpdateTasksTool } from './tools/batch-tools.js';
import { generateSqlQueryTool, executeSqlQueryTool } from './tools/sql-tools.js';
import { sql } from './database.js';

const server = new Server({
  name: 'neon-task-server',
  version: '1.0.0',
}, {
  capabilities: {
    tools: {},
  },
});

// Register all 10 tools
const tools = [
  // Task Management (6 tools)
  createTaskTool,
  listTasksTool,
  updateTaskTool,
  deleteTaskTool,
  getTaskDetailsTool,
  searchTasksByKeywordTool,
  
  // Batch Operations (2 tools)
  batchDeleteTasksTool,
  batchUpdateTasksTool,
  
  // SQL Operations (2 tools)
  generateSqlQueryTool,
  executeSqlQueryTool,
];

server.setRequestHandler('tools/list', async () => ({
  tools: tools.map(t => ({
    name: t.name,
    description: t.description,
    inputSchema: t.inputSchema,
  })),
}));

server.setRequestHandler('tools/call', async (request) => {
  const tool = tools.find(t => t.name === request.params.name);
  if (!tool) {
    throw new Error(`Unknown tool: ${request.params.name}`);
  }
  
  // Extract user_id from request context
  const userId = request.params._meta?.userId || 1;
  
  const result = await tool.execute(request.params.arguments, {
    userId,
    sql,
  });
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

## Package.json

```json
{
  "name": "query-agent-mcp",
  "version": "1.0.0",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "@neondatabase/serverless": "^0.10.0",
    "dotenv": "^16.4.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "tsx": "^4.7.0",
    "typescript": "^5.3.0"
  }
}
```

## TSConfig

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## User Context Handling

The MCP server receives user context from the agent:

```typescript
// In tool execution, extract user from request metadata
const userId = request.params._meta?.userId;

// Use in all database queries
await sql`SELECT * FROM todos WHERE user_id = ${userId}`;
```

## Security Considerations

1. **User Isolation**: Always filter by `user_id` in queries
2. **SQL Injection**: Use parameterized queries (Neon handles this)
3. **Input Validation**: Use Zod schemas for all inputs
4. **Rate Limiting**: Not handled by MCP - implement in agent layer

## Testing

```bash
# Install dependencies
npm install

# Build
npm run build

# Test locally
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | npm start
```

## Deployment

### Local Development
```bash
npm run dev
```

### Production
```bash
npm run build
npm start
```

### Docker (Optional)
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY dist ./dist
CMD ["node", "dist/index.js"]
```

## Key Differences from Current Implementation

| Current (FastAPI) | MCP Server |
|------------------|------------|
| Python async functions | TypeScript async functions |
| SQLModel ORM | Direct SQL with Neon |
| ToolContext from agents SDK | Custom TaskContext |
| FastAPI dependencies | MCP request metadata |
| uvicorn server | stdio transport |

## Migration Checklist

- [ ] Create new repo `query-agent-mcp`
- [ ] Copy tool logic from `backend/app/agent/tools.py`
- [ ] Convert Python to TypeScript
- [ ] Replace SQLModel with Neon SQL
- [ ] Set up MCP server with SDK
- [ ] Test all 10 tools
- [ ] Deploy and get server endpoint
- [ ] Configure in main agent (see MCP_INTEGRATION.md)

## Quick Start Commands

```bash
# Create repo
mkdir query-agent-mcp && cd query-agent-mcp
git init

# Initialize Python project
touch pyproject.toml .env .env.example README.md

# Create structure
mkdir -p src/mcp_server/tools
touch src/mcp_server/__init__.py
touch src/mcp_server/server.py
touch src/mcp_server/database.py
touch src/mcp_server/tools/__init__.py
touch src/mcp_server/tools/task_tools.py
touch src/mcp_server/tools/batch_tools.py
touch src/mcp_server/tools/sql_tools.py

# Install dependencies (using uv)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install mcp asyncpg python-dotenv

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install mcp asyncpg python-dotenv

# Copy tool implementations from this document into files

# Run server
python -m mcp_server.server
```

## Complete Tool Implementation Checklist

### Task Management Tools (6) ✅
- [ ] `create_task` - Include created_by field with username from users table
- [ ] `list_tasks` - Sort by created_at ASC (oldest first), filter by status
- [ ] `update_task` - All fields optional (title, status, description, due_date)
- [ ] `delete_task` - Simple ID-based deletion with user_id security check
- [ ] `get_task_details` - Return all fields including created_by and timestamps
- [ ] `search_tasks_by_keyword` - PostgreSQL ILIKE search on title/description

### Batch Operations Tools (2) ✅
- [ ] `batch_delete_tasks` - Parse comma-separated IDs, max 100 limit, user_id filtering
- [ ] `batch_update_tasks` - Support title, status, description, due_date updates, max 100

### SQL Tools (2) ✅
- [ ] `generate_sql_query` - Regex pattern matching for common natural language queries
- [ ] `execute_sql_query` - SELECT only, user_id requirement, safety checks (no DROP/DELETE/etc)

### Key Implementation Details (Python-Specific)
- **Database**: Use `asyncpg` connection pool (same as main agent)
- **created_by**: Format as `"task created by 'username'"` via JOIN with users table
- **Listing order**: `ORDER BY created_at ASC` (oldest to newest)
- **Optional params**: update_task uses dynamic query building with parameterized queries
- **Batch limits**: Max 100 tasks per batch operation (validated in tool)
- **User isolation**: All queries use `WHERE user_id = $1` for security
- **Timestamps**: `updated_at = NOW()` auto-set on updates
- **Error handling**: Return dict with "error" key for failures, "success" for good results

### Security Requirements
```python
# All tools MUST filter by user_id
async with pool.acquire() as conn:
    result = await conn.fetch(
        "SELECT * FROM todos WHERE user_id = $1",
        user_id  # REQUIRED
    )

# SQL injection prevention - use parameterized queries
# ✅ CORRECT
await conn.fetch("SELECT * FROM todos WHERE id = $1", task_id)

# ❌ WRONG - vulnerable to SQL injection
await conn.fetch(f"SELECT * FROM todos WHERE id = {task_id}")
```

## Testing the MCP Server

### 1. Test locally with Python

```python
# test_server.py
import asyncio
import json
from mcp_server.database import get_db_pool
from mcp_server.tools.task_tools import create_task, list_tasks

async def test():
    pool = await get_db_pool()
    context = {"user_id": 1, "db_pool": pool}
    
    # Test create
    result = await create_task(context, title="Test Task", description="Testing")
    print("Create:", json.dumps(result, indent=2, default=str))
    
    # Test list
    result = await list_tasks(context, status="all")
    print("List:", json.dumps(result, indent=2, default=str))
    
    await pool.close()

asyncio.run(test())
```

### 2. Test with MCP stdio

```bash
# Start server
python -m mcp_server.server

# In another terminal, send JSON-RPC request
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m mcp_server.server
```

### 3. Integration test with main agent

```python
# In main agent (backend/app/agent/mcp_client.py)
from mcp import ClientSession, StdioServerParameters
import asyncio

async def test_mcp():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server"],
        env={"DATABASE_URL": "your_connection_string"}
    )
    
    async with ClientSession(server_params) as session:
        # List tools
        tools = await session.list_tools()
        print(f"Available tools: {len(tools)}")
        
        # Call create_task
        result = await session.call_tool(
            "create_task",
            arguments={"title": "Test from agent"},
            _meta={"user_id": 1}
        )
        print(result)

asyncio.run(test_mcp())
```

## Deployment Options

### Option 1: Local Development
```bash
# Run directly
python -m mcp_server.server

# Run with auto-reload (using watchfiles)
pip install watchfiles
watchfiles 'python -m mcp_server.server' src/
```

### Option 2: Systemd Service (Linux)
```ini
# /etc/systemd/system/query-agent-mcp.service
[Unit]
Description=MCP Neon Task Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/query-agent-mcp
Environment="DATABASE_URL=postgresql://..."
ExecStart=/opt/query-agent-mcp/.venv/bin/python -m mcp_server.server
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 3: Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy source
COPY src/ src/

# Run server
CMD ["python", "-m", "mcp_server.server"]
```

```bash
# Build and run
docker build -t query-agent-mcp .
docker run -e DATABASE_URL="postgresql://..." query-agent-mcp
```

## Key Differences from Current Implementation

| Current (Inline Tools) | MCP Server (Separate) |
|------------------------|----------------------|
| Tools in `backend/app/agent/tools.py` | Tools in `src/mcp_server/tools/*.py` |
| Direct SQLModel ORM | asyncpg connection pool |
| ToolContext from agents SDK | Custom dict context |
| FastAPI dependencies injection | MCP metadata passing |
| Runs in same process | Separate process/service |
| Tightly coupled | Loosely coupled via MCP protocol |

## Migration Checklist

### Pre-Migration (Current State)
- [x] 10 tools working in `backend/app/agent/tools.py`
- [x] All features: batch ops, created_by, ASC order, optional params
- [x] Tools registered in `backend/app/agent/factory.py`
- [x] Server running and tested

### MCP Server Creation
- [ ] Create new repo `query-agent-mcp`
- [ ] Set up Python project structure
- [ ] Copy tool logic from `backend/app/agent/tools.py`
- [ ] Convert from SQLModel to asyncpg queries
- [ ] Implement MCP server.py with tool registration
- [ ] Test all 10 tools standalone
- [ ] Set up environment variables

### Integration with Main Agent
- [ ] Install MCP client in main agent
- [ ] Create `backend/app/agent/mcp_client.py`
- [ ] Update `factory.py` to use MCP tools
- [ ] Update router to pass user context to MCP
- [ ] Test end-to-end integration
- [ ] Verify user_id isolation works
- [ ] Performance testing

### Post-Migration
- [ ] Archive old `tools.py` (don't delete until fully tested)
- [ ] Update documentation
- [ ] Deploy MCP server to production
- [ ] Monitor for issues

## Compatibility Notes

### Database
- ✅ Same Neon PostgreSQL database
- ✅ Same schema (users, todos, conversation_messages)
- ✅ Same asyncpg driver family
- ✅ User isolation via user_id

### Python Environment
- ✅ Python 3.11+ (same as main agent)
- ✅ Async/await (same pattern)
- ✅ Type hints supported
- ✅ Same error handling patterns

### Data Format
- ✅ Same datetime handling (ISO format)
- ✅ Same status values ('pending', 'completed')
- ✅ Same created_by format
- ✅ Compatible JSON responses

## Troubleshooting

### Connection Issues
```bash
# Test database connection
python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

### Tool Execution Errors
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### MCP Protocol Issues
```bash
# Check MCP SDK version
pip show mcp

# Update if needed
pip install --upgrade mcp
```

This Python-based MCP server is fully compatible with your Python agent! 🎉

#By WeWise Labs
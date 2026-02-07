# CONTEXT.md — Intent Freezer

> **Authority: Level 5**
> Defines WHY this system exists and WHAT it is NOT.
> Immutable unless user explicitly changes it.

---

```slc
@block CONTEXT project_goal
priority: critical
intent: "Define project purpose and boundaries"
scope: global
depends_on: none

content:
  goal: |
    Create a standalone Python MCP (Model Context Protocol) server that exposes
    10 task management tools for Neon PostgreSQL database operations.
    
    This server enables LLM agents to perform CRUD operations, batch operations,
    and SQL queries on a task management system with user isolation and security.
    
  purpose: |
    - Extract task management tools from existing FastAPI backend
    - Make tools available via MCP protocol (stdio transport)
    - Maintain compatibility with existing Neon database schema
    - Enable reusable task management for multiple agent systems
@end
```

---

## GOAL

**Primary Objective:**

Create a production-ready Python MCP server (`query-agent-mcp`) that:

1. Implements **10 tools** (6 task management, 2 batch operations, 2 SQL operations)
2. Connects to **Neon PostgreSQL** via `asyncpg`
3. Enforces **user isolation** (all queries filter by `user_id`)
4. Communicates via **stdio transport** using MCP Python SDK
5. Maintains **compatibility** with existing database schema

**Success Criteria:**

- ✅ All 10 tools functional and tested
- ✅ User isolation enforced in all database queries
- ✅ MCP protocol compliance (tools/list, tools/call)
- ✅ Error handling with structured responses
- ✅ Ready for integration with main agent

---

## NON-GOALS

```slc
@block CONTEXT non_goals
priority: critical
intent: "Explicit exclusions — features we will NOT build"
scope: global

content:
  excluded_features:
    - "Authentication/Authorization (handled by main agent)"
    - "Frontend UI (server-only)"
    - "REST API endpoints (MCP stdio only)"
    - "Database migrations (schema already exists)"
    - "User management (uses existing users table)"
    - "Rate limiting (agent layer responsibility)"
    - "Caching layer (direct DB queries)"
    - "GraphQL or other query languages"
    - "Websocket transport (stdio only)"
    - "Multi-database support (Neon PostgreSQL only)"
    
  not_in_scope:
    - "Changing database schema"
    - "Creating new tables"
    - "TypeScript version (Python only)"
    - "HTTP transport mode"
    - "Tool versioning or backward compatibility"
@end
```

**Key Exclusions:**

1. **No authentication** — User context passed from agent
2. **No frontend** — Server-side tools only
3. **No schema changes** — Use existing Neon database
4. **No HTTP/REST** — MCP stdio transport only
5. **No multi-database** — Neon PostgreSQL only

---

## USER PERSONAS

```slc
@block CONTEXT personas
priority: medium
intent: "Who will use this system and how"
scope: global

content:
  primary_users:
    - role: "LLM Agent"
      needs: "Execute task operations via MCP protocol"
      context: "Receives user_id from main agent system"
      
    - role: "Backend Developer"
      needs: "Integrate MCP server with FastAPI agent"
      context: "Uses stdio to communicate with server"
      
    - role: "DevOps Engineer"
      needs: "Deploy and monitor MCP server"
      context: "Systemd service or Docker container"
@end
```

---

## SYSTEM BOUNDARIES

```slc
@block CONTEXT boundaries
priority: high
intent: "Clear system boundaries and interfaces"
scope: global

content:
  input_boundary:
    - "MCP protocol requests (JSON-RPC 2.0)"
    - "User context from agent (_meta.userId)"
    - "Tool arguments (validated per tool schema)"
    
  output_boundary:
    - "MCP protocol responses (TextContent)"
    - "Structured JSON results (success/error)"
    - "Database query results"
    
  data_boundary:
    - "Neon PostgreSQL database (existing schema)"
    - "Three tables: users, todos, conversation_messages"
    - "Read/Write access to todos table"
    - "Read-only access to users table"
    
  integration_points:
    - "Main agent system (via stdio)"
    - "Neon database (via asyncpg)"
    - "Environment variables (.env file)"
@end
```

---

## CONSTRAINTS PREVIEW

*See CONSTRAINTS.md for full technical constraints*

Key limitations:
- Python 3.11+ only
- asyncpg for database (no ORM)
- MCP Python SDK >= 1.0.0
- Neon PostgreSQL (no other databases)
- stdio transport (no HTTP/WebSocket)

---

## DECISION LOG PREVIEW

*See MEMORY.md for frozen decisions*

Key decisions:
- Use Python (not TypeScript) — aligns with main agent
- Use asyncpg (not SQLModel) — lightweight, direct SQL
- Use stdio transport (not HTTP) — standard MCP pattern
- Individual task files (not monolithic) — context efficiency

---

```slc
@block CONTEXT immutability_marker
priority: critical
intent: "Mark this file as immutable"
scope: global

content:
  status: "frozen"
  approved_by: "user"
  approved_date: "2026-02-07"
  
  change_protocol: |
    To change CONTEXT.md:
    1. User must explicitly request change
    2. Update MEMORY.md with reason
    3. Re-evaluate all dependent files
    4. Re-validate ARCH.md and PLAN.md
@end
```

---

*End of CONTEXT.md — Read CONSTRAINTS.md next*

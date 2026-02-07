# ARCH.md — System Architecture

> **Authority: Level 6**
> Defines system architecture, data models, control flow, and boundaries.
> No tasks. No code. Pure architecture.

---

```slc
@block ARCH system_overview
priority: critical
intent: "High-level system architecture"
scope: global
depends_on: [CONTEXT.project_goal, CONSTRAINTS.tech_stack]

content:
  architecture_type: "MCP Server (stdio transport)"
  pattern: "Tool-based agent interface"
  
  components:
    - "MCP Server (server.py) — Entry point and routing"
    - "Database Layer (database.py) — Connection pool management"
    - "Tool Modules (tools/) — Business logic"
    - "Environment Config (.env) — Secrets and configuration"
    
  data_flow: |
    Agent → stdio → MCP Server → Tool Function → Database → Response
@end
```

---

## COMPONENT ARCHITECTURE

```slc
@block ARCH components
priority: critical
intent: "Detailed component definitions and responsibilities"
scope: global

content:
  component_diagram: |
    ┌─────────────────────────────────────────┐
    │         Main Agent (External)           │
    │    (Passes user_id via MCP metadata)    │
    └────────────────┬────────────────────────┘
                     │ stdio (JSON-RPC 2.0)
    ┌────────────────▼────────────────────────┐
    │         MCP Server (server.py)          │
    │  - Tool registration                    │
    │  - Request routing                      │
    │  - Context building (user_id + pool)    │
    └────────┬───────────────┬────────────────┘
             │               │
    ┌────────▼────────┐  ┌───▼──────────────┐
    │  Database Layer │  │   Tool Modules    │
    │  (database.py)  │  │   (tools/)        │
    │  - Pool mgmt    │  │  - task_tools.py  │
    │  - Connection   │  │  - batch_tools.py │
    │                 │  │  - sql_tools.py   │
    └────────┬────────┘  └───┬──────────────┘
             │               │
             └───────┬───────┘
    ┌────────────────▼────────────────────────┐
    │      Neon PostgreSQL (External)         │
    │  - users table (read-only)              │
    │  - todos table (read/write)             │
    │  - conversation_messages (not used)     │
    └─────────────────────────────────────────┘
@end
```

### Component Responsibilities

```slc
@block ARCH component_server
priority: critical
intent: "MCP Server component specification"
scope: backend

content:
  file: "src/mcp_server/server.py"
  
  responsibilities:
    - "Initialize MCP server instance"
    - "Register 10 tools with schemas"
    - "Handle tools/list requests"
    - "Handle tools/call requests"
    - "Extract user_id from MCP metadata"
    - "Build tool context (user_id + pool)"
    - "Route to appropriate tool function"
    - "Serialize results as TextContent"
    - "Manage server lifecycle (startup/shutdown)"
    
  dependencies:
    - "mcp.server.Server"
    - "mcp.server.stdio.stdio_server"
    - "database.get_db_pool, close_db_pool"
    - "All tool functions"
    
  interfaces:
    input: "MCP JSON-RPC 2.0 requests via stdin"
    output: "MCP JSON-RPC 2.0 responses via stdout"
    
  lifecycle:
    startup:
      - "Load environment variables"
      - "Initialize database pool"
      - "Create MCP server instance"
      - "Register tools"
      - "Start stdio transport"
      
    runtime:
      - "Listen for requests"
      - "Route to tool functions"
      - "Return responses"
      
    shutdown:
      - "Close database pool"
      - "Clean up resources"
@end
```

```slc
@block ARCH component_database
priority: critical
intent: "Database layer component specification"
scope: backend

content:
  file: "src/mcp_server/database.py"
  
  responsibilities:
    - "Manage asyncpg connection pool"
    - "Provide get_db_pool() factory"
    - "Provide close_db_pool() cleanup"
    - "Handle connection errors"
    
  configuration:
    pool_size_min: 1
    pool_size_max: 10
    timeout: 30
    ssl_mode: "require"
    
  connection_string:
    source: "DATABASE_URL environment variable"
    format: "postgresql://user:pass@host/db?sslmode=require"
    
  error_handling:
    - "Raise ValueError if DATABASE_URL not set"
    - "Handle connection failures gracefully"
    - "Log connection errors"
@end
```

```slc
@block ARCH component_tools
priority: critical
intent: "Tool modules architecture"
scope: backend

content:
  modules:
    task_tools:
      file: "src/mcp_server/tools/task_tools.py"
      functions: 6
      tools:
        - create_task
        - list_tasks
        - update_task
        - delete_task
        - get_task_details
        - search_tasks_by_keyword
        
    batch_tools:
      file: "src/mcp_server/tools/batch_tools.py"
      functions: 2
      tools:
        - batch_delete_tasks
        - batch_update_tasks
        
    sql_tools:
      file: "src/mcp_server/tools/sql_tools.py"
      functions: 2
      tools:
        - generate_sql_query
        - execute_sql_query
        
  tool_function_signature:
    pattern: "async def tool_name(context: dict, **kwargs) -> dict"
    
    context_structure:
      user_id: "int — User ID for query filtering"
      db_pool: "asyncpg.Pool — Database connection pool"
      
    return_structure:
      success_case:
        success: true
        data: "Result data"
        message: "User-friendly message"
        
      error_case:
        error: "Error message"
        code: "Error code (optional)"
@end
```

---

## DATA MODELS

```slc
@block ARCH data_model_users
priority: high
intent: "Users table data model (read-only)"
scope: backend

content:
  table: "users"
  access: "read-only"
  
  schema:
    id:
      type: "SERIAL PRIMARY KEY"
      description: "Unique user identifier"
      
    username:
      type: "VARCHAR NOT NULL UNIQUE"
      description: "User login name"
      
    email:
      type: "VARCHAR NOT NULL UNIQUE"
      description: "User email address"
      
    hashed_password:
      type: "VARCHAR NOT NULL"
      description: "Password hash (not used by this server)"
      
    created_at:
      type: "TIMESTAMP DEFAULT NOW()"
      description: "Account creation timestamp"
      
  usage:
    - "Lookup username for created_by field"
    - "No inserts, updates, or deletes"
@end
```

```slc
@block ARCH data_model_todos
priority: critical
intent: "Todos table data model (read/write)"
scope: backend

content:
  table: "todos"
  access: "read/write"
  
  schema:
    id:
      type: "SERIAL PRIMARY KEY"
      description: "Unique task identifier"
      auto_increment: true
      
    title:
      type: "VARCHAR(255) NOT NULL"
      description: "Task title"
      constraints: "Non-empty, 1-255 characters"
      
    description:
      type: "VARCHAR(1000) DEFAULT NULL"
      description: "Task description (optional)"
      constraints: "0-1000 characters, nullable"
      
    status:
      type: "VARCHAR DEFAULT 'pending'"
      description: "Task status"
      allowed_values: ["pending", "completed"]
      
    due_date:
      type: "TIMESTAMP DEFAULT NULL"
      description: "Task due date (optional)"
      format: "ISO 8601"
      
    user_id:
      type: "INTEGER REFERENCES users(id)"
      description: "Owner user ID"
      constraints: "MUST be present in ALL queries (security)"
      
    created_by:
      type: "VARCHAR(100) DEFAULT NULL"
      description: "Audit field"
      format: "task created by 'username'"
      
    created_at:
      type: "TIMESTAMP DEFAULT NOW()"
      description: "Creation timestamp"
      auto_set: true
      
    updated_at:
      type: "TIMESTAMP DEFAULT NULL"
      description: "Last update timestamp"
      auto_set: "on UPDATE"
      
  indexes:
    - "PRIMARY KEY (id)"
    - "INDEX ON user_id"
    - "INDEX ON status"
    
  security:
    - "ALL queries MUST filter by user_id"
    - "Use parameterized queries only"
@end
```

---

## CONTROL FLOW

```slc
@block ARCH flow_tool_execution
priority: critical
intent: "Tool execution control flow"
scope: backend

content:
  sequence:
    1. "Agent sends MCP request via stdin"
    2. "Server receives JSON-RPC request"
    3. "Server extracts tool name and arguments"
    4. "Server extracts user_id from _meta.userId"
    5. "Server builds context dict {user_id, db_pool}"
    6. "Server calls tool function with context + args"
    7. "Tool function executes business logic"
    8. "Tool function queries database (filtered by user_id)"
    9. "Tool function returns result dict"
    10. "Server serializes result as TextContent"
    11. "Server sends JSON-RPC response via stdout"
    
  example_flow: |
    # Agent request
    {
      "method": "tools/call",
      "params": {
        "name": "create_task",
        "arguments": {"title": "New Task"},
        "_meta": {"userId": 42}
      }
    }
    
    # Server processing
    user_id = 42
    context = {"user_id": 42, "db_pool": pool}
    result = await create_task(context, title="New Task")
    
    # Server response
    {
      "result": {
        "content": [
          {"type": "text", "text": "{\"success\": true, ...}"}
        ]
      }
    }
@end
```

```slc
@block ARCH flow_database_query
priority: critical
intent: "Database query execution flow"
scope: backend

content:
  sequence:
    1. "Tool function receives context"
    2. "Extract user_id from context"
    3. "Extract db_pool from context"
    4. "Acquire connection from pool"
    5. "Execute parameterized query with user_id filter"
    6. "Process results"
    7. "Release connection back to pool"
    8. "Return structured result"
    
  example: |
    async def list_tasks(context, status="all"):
        user_id = context["user_id"]
        pool = context["db_pool"]
        
        async with pool.acquire() as conn:
            tasks = await conn.fetch(
                "SELECT * FROM todos WHERE user_id = $1",
                user_id
            )
            
        return {
            "success": True,
            "tasks": [dict(t) for t in tasks]
        }
        
  error_handling:
    - "Catch asyncpg exceptions"
    - "Return structured error dict"
    - "Never expose stack traces"
@end
```

---

## BOUNDARIES & INTERFACES

```slc
@block ARCH boundaries
priority: high
intent: "System boundaries and external interfaces"
scope: backend

content:
  external_systems:
    main_agent:
      type: "MCP Client"
      protocol: "JSON-RPC 2.0 over stdio"
      responsibility: "Authentication, user session management"
      provides: "user_id via MCP metadata"
      
    neon_database:
      type: "PostgreSQL 14+"
      protocol: "asyncpg (PostgreSQL wire protocol)"
      responsibility: "Data persistence"
      provides: "users and todos tables"
      
  internal_boundaries:
    server_layer:
      responsibility: "MCP protocol, routing"
      interfaces: "Tool registration, request handling"
      
    database_layer:
      responsibility: "Connection management"
      interfaces: "get_db_pool(), close_db_pool()"
      
    tool_layer:
      responsibility: "Business logic"
      interfaces: "Tool functions (async def)"
@end
```

---

## TOOL SCHEMAS

```slc
@block ARCH tool_schema_create_task
priority: critical
intent: "create_task tool specification"
scope: backend

content:
  name: "create_task"
  description: "Create a new task with automatic created_by tracking"
  
  parameters:
    title:
      type: "string"
      required: true
      description: "Task title (1-255 characters)"
      
    description:
      type: "string"
      required: false
      default: ""
      description: "Task description (0-1000 characters)"
      
    due_date:
      type: "string"
      required: false
      description: "Due date (ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
      
  returns:
    success:
      success: true
      task_id: "int"
      message: "string"
      
    error:
      error: "string"
      
  implementation_notes:
    - "Fetch username from users table for created_by"
    - "Parse due_date with datetime.fromisoformat()"
    - "Format created_by as 'task created by \\'username\\''"
    - "Auto-set created_at timestamp"
@end
```

```slc
@block ARCH tool_schema_list_tasks
priority: critical
intent: "list_tasks tool specification"
scope: backend

content:
  name: "list_tasks"
  description: "List all tasks (sorted oldest to newest)"
  
  parameters:
    status:
      type: "string"
      required: false
      default: "all"
      allowed_values: ["all", "pending", "completed"]
      description: "Filter tasks by status"
      
  returns:
    success:
      success: true
      count: "int"
      tasks: "array of task objects"
      
  implementation_notes:
    - "ORDER BY created_at ASC (oldest first)"
    - "Filter by user_id AND status (if not 'all')"
    - "Return all fields: id, title, description, status, due_date, created_by, created_at, updated_at"
@end
```

```slc
@block ARCH tool_schema_update_task
priority: critical
intent: "update_task tool specification"
scope: backend

content:
  name: "update_task"
  description: "Update a single task (all fields optional)"
  
  parameters:
    task_id:
      type: "number"
      required: true
      description: "Task ID to update"
      
    title:
      type: "string"
      required: false
      description: "New title"
      
    status:
      type: "string"
      required: false
      allowed_values: ["pending", "completed"]
      description: "New status"
      
    description:
      type: "string"
      required: false
      description: "New description"
      
    due_date:
      type: "string"
      required: false
      description: "New due date or 'none' to clear"
      
  implementation_notes:
    - "Build dynamic UPDATE query based on provided fields"
    - "All fields optional (at least one required)"
    - "Auto-set updated_at = NOW()"
    - "Validate status enum"
    - "Handle due_date='none' as NULL"
@end
```

```slc
@block ARCH tool_schema_delete_task
priority: high
intent: "delete_task tool specification"
scope: backend

content:
  name: "delete_task"
  description: "Delete a single task by ID"
  
  parameters:
    task_id:
      type: "number"
      required: true
      description: "Task ID to delete"
      
  returns:
    success:
      success: true
      message: "string"
      
    error:
      error: "string"
      
  implementation_notes:
    - "DELETE WHERE id = $1 AND user_id = $2"
    - "Return error if task not found"
@end
```

```slc
@block ARCH tool_schema_get_task_details
priority: medium
intent: "get_task_details tool specification"
scope: backend

content:
  name: "get_task_details"
  description: "Get detailed information about a task"
  
  parameters:
    task_id:
      type: "number"
      required: true
      description: "Task ID"
      
  returns:
    success:
      success: true
      task: "object with all fields"
@end
```

```slc
@block ARCH tool_schema_search_tasks
priority: medium
intent: "search_tasks_by_keyword tool specification"
scope: backend

content:
  name: "search_tasks_by_keyword"
  description: "Search for tasks using fuzzy matching"
  
  parameters:
    keyword:
      type: "string"
      required: true
      description: "Search keyword"
      
  implementation_notes:
    - "Use PostgreSQL ILIKE for case-insensitive search"
    - "Search in both title and description"
    - "Pattern: WHERE (title ILIKE '%keyword%' OR description ILIKE '%keyword%')"
@end
```

```slc
@block ARCH tool_schema_batch_delete
priority: critical
intent: "batch_delete_tasks tool specification"
scope: backend

content:
  name: "batch_delete_tasks"
  description: "Delete multiple tasks by IDs (max 100)"
  
  parameters:
    task_ids:
      type: "string"
      required: true
      format: "comma-separated IDs"
      example: "1,2,3,42,100"
      max_items: 100
      
  implementation_notes:
    - "Parse comma-separated string to int array"
    - "Validate max 100 items"
    - "Use WHERE id = ANY($1::int[]) AND user_id = $2"
    - "Report deleted IDs and missing IDs separately"
@end
```

```slc
@block ARCH tool_schema_batch_update
priority: critical
intent: "batch_update_tasks tool specification"
scope: backend

content:
  name: "batch_update_tasks"
  description: "Update multiple tasks with same values (max 100)"
  
  parameters:
    task_ids:
      type: "string"
      required: true
      format: "comma-separated IDs"
      max_items: 100
      
    title:
      type: "string"
      required: false
      
    status:
      type: "string"
      required: false
      allowed_values: ["pending", "completed"]
      
    description:
      type: "string"
      required: false
      
    due_date:
      type: "string"
      required: false
      
  implementation_notes:
    - "Similar to update_task but uses ANY($1::int[]) for multiple IDs"
    - "All value fields optional (at least one required)"
    - "Apply same value to all specified tasks"
@end
```

```slc
@block ARCH tool_schema_generate_sql
priority: medium
intent: "generate_sql_query tool specification"
scope: backend

content:
  name: "generate_sql_query"
  description: "Generate SQL from natural language"
  
  parameters:
    question:
      type: "string"
      required: true
      description: "Natural language question"
      
  implementation_notes:
    - "Use regex pattern matching for common queries"
    - "Return suggested SQL query as string"
    - "Do NOT execute (only generate)"
    - "Include user_id filter in generated queries"
@end
```

```slc
@block ARCH tool_schema_execute_sql
priority: critical
intent: "execute_sql_query tool specification"
scope: backend

content:
  name: "execute_sql_query"
  description: "Execute SELECT queries safely"
  
  parameters:
    query:
      type: "string"
      required: true
      description: "SQL SELECT query"
      
  security_checks:
    - "Query must start with SELECT (case-insensitive)"
    - "Query must NOT contain DDL keywords (DROP, DELETE, UPDATE, etc.)"
    - "Query must include user_id filter"
    - "Limit results to 50 rows in display"
    
  implementation_notes:
    - "Validate query before execution"
    - "Execute with 30-second timeout"
    - "Format results as table"
@end
```

---

## ERROR HANDLING STRATEGY

```slc
@block ARCH error_handling
priority: high
intent: "Global error handling approach"
scope: backend

content:
  error_types:
    validation_errors:
      examples: "Invalid status, invalid date format"
      response: '{"error": "❌ Validation error message"}'
      
    database_errors:
      examples: "Connection failure, query timeout"
      response: '{"error": "❌ Database error (generic)"}'
      logging: "Log full error internally"
      
    not_found_errors:
      examples: "Task not found, user not found"
      response: '{"error": "❌ Resource not found"}'
      
    security_errors:
      examples: "Missing user_id, SQL injection attempt"
      response: '{"error": "❌ Invalid request"}'
      logging: "Log as security violation"
      
  error_response_format:
    structure:
      error: "string — User-friendly message"
      code: "string — Error code (optional)"
      
  no_stack_traces: "Never return stack traces to client"
@end
```

---

*End of ARCH.md — Read PLAN.md next*

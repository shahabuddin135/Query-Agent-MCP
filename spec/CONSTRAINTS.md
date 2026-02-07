# CONSTRAINTS.md — Reality Anchor

> **Authority: Level 4**
> Defines HARD LIMITS that override all plans and preferences.
> These constraints are non-negotiable.

---

```slc
@block CONSTRAINTS tech_stack
priority: critical
intent: "Frozen technology choices"
scope: global
depends_on: [CONTEXT.project_goal]

content:
  language: "Python 3.11+"
  protocol: "MCP (Model Context Protocol)"
  transport: "Streamable HTTP (via Starlette + uvicorn)"
  database: "Neon PostgreSQL"
  
  required_libraries:
    - name: "mcp"
      version: ">=1.0.0"
      purpose: "MCP Python SDK"
      
    - name: "asyncpg"
      version: ">=0.29.0"
      purpose: "Async PostgreSQL driver"
      
    - name: "python-dotenv"
      version: ">=1.0.0"
      purpose: "Environment variables"
      
    - name: "uvicorn"
      version: ">=0.30.0"
      purpose: "ASGI server for Streamable HTTP transport"
      
    - name: "starlette"
      version: "*"
      purpose: "ASGI framework (used by MCP SDK for HTTP transport)"
      
  forbidden_libraries:
    - "sqlalchemy" # Too heavy for this use case
    - "sqlmodel" # Not needed, using direct SQL
    - "requests" # No HTTP client needed
    - "psycopg2" # Use asyncpg instead
@end
```

---

## TECH STACK

### Language & Runtime

```slc
@block CONSTRAINTS runtime
priority: critical
intent: "Runtime environment requirements"
scope: global

content:
  python_version: "3.11+"
  async_support: "required"
  type_hints: "recommended"
  
  rationale: |
    - Python 3.11+ for modern async features
    - Type hints for IDE support and documentation
    - Async required for asyncpg and MCP SDK
@end
```

### Dependencies

**Required:**

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp` | >= 1.0.0 | MCP Python SDK |
| `asyncpg` | >= 0.29.0 | PostgreSQL async driver |
| `python-dotenv` | >= 1.0.0 | Environment configuration |

**Forbidden:**

- SQLAlchemy, SQLModel (use direct SQL)
- psycopg2 (use asyncpg)
- Any HTTP clients (not needed)

---

## SCALE & PERFORMANCE

```slc
@block CONSTRAINTS scale
priority: high
intent: "Expected usage limits and performance targets"
scope: global

content:
  expected_load:
    - "Single agent process (not multi-tenant)"
    - "1-10 concurrent tool calls max"
    - "< 100ms per simple query"
    - "< 500ms per complex query"
    
  database_limits:
    - "Connection pool: 1-10 connections"
    - "Query timeout: 30 seconds"
    - "Batch operations: max 100 items"
    
  not_designed_for:
    - "High concurrency (1000+ req/sec)"
    - "Large result sets (> 1000 rows)"
    - "Long-running queries (> 1 minute)"
    - "Real-time streaming"
@end
```

---

## HARD RULES

```slc
@block CONSTRAINTS hard_rules
priority: critical
intent: "Non-negotiable constraints that cannot be violated"
scope: global

content:
  database_rules:
    - "ALL queries MUST filter by user_id"
    - "Use parameterized queries ONLY (no string interpolation)"
    - "No DDL operations (no CREATE/ALTER/DROP)"
    - "Read-only access to users table"
    - "Read/Write access to todos table only"
    
  mcp_rules:
    - "Streamable HTTP transport (ASGI via Starlette + uvicorn)"
    - "API key authentication on all /mcp requests"
    - "JSON-RPC 2.0 protocol compliance"
    - "Tool names must match registration exactly"
    - "All tool responses must be TextContent type"
    
  security_rules:
    - "User isolation enforced in ALL queries"
    - "No SQL injection vectors allowed"
    - "No credential logging"
    - "Environment variables for secrets only"
    
  code_rules:
    - "All functions must be async"
    - "All database queries use asyncpg"
    - "All errors must return structured dicts"
    - "No print() statements (logging only)"
@end
```

---

## DATABASE SCHEMA (FIXED)

```slc
@block CONSTRAINTS database_schema
priority: critical
intent: "Fixed database schema — cannot be modified"
scope: global

content:
  schema_version: "existing"
  modification_allowed: false
  
  tables:
    users:
      purpose: "Read-only user lookup"
      fields:
        - "id SERIAL PRIMARY KEY"
        - "username VARCHAR NOT NULL UNIQUE"
        - "email VARCHAR NOT NULL UNIQUE"
        - "hashed_password VARCHAR NOT NULL"
        - "created_at TIMESTAMP DEFAULT NOW()"
        
    todos:
      purpose: "Main task storage (read/write)"
      fields:
        - "id SERIAL PRIMARY KEY"
        - "title VARCHAR(255) NOT NULL"
        - "description VARCHAR(1000) DEFAULT NULL"
        - "status VARCHAR DEFAULT 'pending'"
        - "due_date TIMESTAMP DEFAULT NULL"
        - "user_id INTEGER REFERENCES users(id)"
        - "created_by VARCHAR(100) DEFAULT NULL"
        - "created_at TIMESTAMP DEFAULT NOW()"
        - "updated_at TIMESTAMP DEFAULT NULL"
        
    conversation_messages:
      purpose: "Not used by this server (read-only if needed)"
      access: "read-only"
@end
```

---

## PROJECT STRUCTURE (FIXED)

```slc
@block CONSTRAINTS project_structure
priority: critical
intent: "Required directory structure"
scope: global

content:
  root_structure: |
    query-agent-mcp/
    ├── src/
    │   └── mcp_server/
    │       ├── __init__.py
    │       ├── server.py
    │       ├── database.py
    │       └── tools/
    │           ├── __init__.py
    │           ├── task_tools.py
    │           ├── batch_tools.py
    │           └── sql_tools.py
    ├── spec/               # This directory
    ├── .env
    ├── .env.example
    ├── pyproject.toml
    ├── README.md
    └── requirements.txt
    
  rationale: |
    - src/ for source code
    - spec/ for SLC specifications (this directory)
    - Tools grouped by category in separate files
    - Standard Python package structure
@end
```

---

## ENVIRONMENT VARIABLES

```slc
@block CONSTRAINTS environment
priority: critical
intent: "Required environment configuration"
scope: global

content:
  required_vars:
    DATABASE_URL:
      format: "postgresql://user:pass@host/db?sslmode=require"
      example: "postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
      required: true
      
    MCP_API_KEY:
      format: "string (min 32 characters)"
      example: "your-secure-api-key-here-min-32-chars"
      required: true
      purpose: "Authenticates HTTP requests to the MCP endpoint"
      
    MCP_SERVER_NAME:
      format: "string"
      default: "neon-task-server"
      required: false
      
    MCP_SERVER_VERSION:
      format: "semver"
      default: "1.0.0"
      required: false
      
  forbidden_vars:
    - "PROD_DATABASE_URL" # Use DATABASE_URL only
@end
```

---

## FILE SIZE & COMPLEXITY LIMITS

```slc
@block CONSTRAINTS file_limits
priority: medium
intent: "Code organization and maintainability limits"
scope: global

content:
  file_size_limits:
    - "task_tools.py: < 500 lines"
    - "batch_tools.py: < 300 lines"
    - "sql_tools.py: < 200 lines"
    - "server.py: < 400 lines"
    - "database.py: < 100 lines"
    
  function_limits:
    - "Max 50 lines per function"
    - "Max 4 levels of nesting"
    - "Max 5 parameters per function"
    
  rationale: |
    Keep code readable and maintainable.
    Split large functions if limits exceeded.
@end
```

---

## COMPATIBILITY REQUIREMENTS

```slc
@block CONSTRAINTS compatibility
priority: high
intent: "Compatibility with existing systems"
scope: global

content:
  must_work_with:
    - "Existing Neon PostgreSQL database"
    - "Existing users and todos tables"
    - "FastAPI main agent (stdio integration)"
    - "Python 3.11+ environments"
    
  data_format_compatibility:
    - "ISO 8601 datetime strings"
    - "Status values: 'pending' or 'completed' only"
    - "created_by format: 'task created by \'username\''"
    - "JSON-compatible data types only"
@end
```

---

## DEPLOYMENT CONSTRAINTS

```slc
@block CONSTRAINTS deployment
priority: medium
intent: "Deployment environment requirements"
scope: global

content:
  supported_environments:
    - "Railway (Docker container)"
    - "Docker container (any host)"
    - "Local development (Windows/Mac/Linux)"
    
  required_access:
    - "Network access to Neon PostgreSQL"
    - "Environment variable configuration (DATABASE_URL, MCP_API_KEY)"
    - "Streamable HTTP for MCP communication (port from PORT env var)"
    
  deployment_method:
    transport: "Streamable HTTP (ASGI)"
    server: "uvicorn"
    endpoint: "/mcp"
    authentication: "API key via Authorization: Bearer header"
    
  not_supported:
    - "Serverless (Lambda, Cloud Functions)"
    - "Browser/WASM environments"
    - "Embedded systems"
@end
```

---

```slc
@block CONSTRAINTS violation_handling
priority: critical
intent: "What to do when constraints are violated"
scope: global

content:
  if_constraint_violated:
    - "STOP execution immediately"
    - "Report constraint name and violation details"
    - "Ask user for explicit override or solution"
    - "Do NOT attempt workarounds"
    
  examples:
    - "If query missing user_id → ABORT with error"
    - "If using SQLAlchemy → REJECT and require asyncpg"
    - "If tool returns wrong type → FAIL and fix"
@end
```

---

*End of CONSTRAINTS.md — Read SECURITY.md next*

# Query Agent MCP Server

A Model Context Protocol (MCP) server that provides 10 powerful tools for task management and SQL operations with Neon PostgreSQL.

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Neon PostgreSQL database
- MCP-compatible client (Claude Desktop, Continue, etc.)

### Installation

1. **Clone and setup:**
```bash
cd query-agent-mcp
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Neon database connection string:
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
```

### Running the Server

**Test database connection:**
```bash
python test_db_connection.py
```

**Test server startup:**
```bash
python test_server_startup.py
```

**Run the MCP server:**
```bash
python -m src.mcp_server
```

## 🔧 MCP Client Configuration

Add this to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "query-agent": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "D:\\my-projects\\query-agent-mcp",
      "env": {
        "DATABASE_URL": "postgresql://user:password@host/database?sslmode=require"
      }
    }
  }
}
```

Or use the absolute path to your virtual environment:

```json
{
  "mcpServers": {
    "query-agent": {
      "command": "D:\\my-projects\\query-agent-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp_server"],
      "cwd": "D:\\my-projects\\query-agent-mcp"
    }
  }
}
```

## 🛠️ Available Tools

### Task Management (6 tools)

#### 1. `create_task`
Create a new task for a user.

**Parameters:**
- `user_id` (required): User ID who owns the task
- `title` (required): Task title
- `description` (optional): Task description  
- `due_date` (optional): Due date timestamp

**Example:**
```json
{
  "user_id": 1,
  "title": "Complete project documentation",
  "description": "Write comprehensive README with all tool examples",
  "due_date": null
}
```

**Returns:**
```json
{
  "success": true,
  "task_id": 42,
  "message": "✅ Created task #42: 'Complete project documentation'"
}
```

#### 2. `list_tasks`
List all tasks for a user with optional filtering.

**Parameters:**
- `user_id` (required): User ID
- `status` (optional): Filter by status - `pending`, `in_progress`, or `completed`

**Example:**
```json
{
  "user_id": 1,
  "status": "pending"
}
```

**Returns:**
```json
{
  "success": true,
  "count": 3,
  "tasks": [
    {
      "id": 1,
      "title": "Task 1",
      "description": "Description",
      "status": "pending",
      "user_id": 1,
      "created_at": "2026-02-07T10:00:00",
      "updated_at": null,
      "due_date": null,
      "created_by": "task created by 'username'"
    }
  ]
}
```

#### 3. `update_task`
Update an existing task (any combination of fields).

**Parameters:**
- `user_id` (required): User ID for authorization
- `task_id` (required): Task ID to update
- `title` (optional): New title
- `description` (optional): New description
- `status` (optional): New status - `pending`, `in_progress`, or `completed`
- `due_date` (optional): New due date or `"none"` to clear

**Example:**
```json
{
  "user_id": 1,
  "task_id": 42,
  "status": "completed"
}
```

#### 4. `delete_task`
Delete a task.

**Parameters:**
- `user_id` (required): User ID for authorization
- `task_id` (required): Task ID to delete

#### 5. `get_task_details`
Get detailed information about a specific task.

**Parameters:**
- `user_id` (required): User ID for authorization
- `task_id` (required): Task ID

#### 6. `search_tasks_by_keyword`
Search tasks by keyword in title or description (case-insensitive).

**Parameters:**
- `user_id` (required): User ID
- `keyword` (required): Search keyword

**Example:**
```json
{
  "user_id": 1,
  "keyword": "documentation"
}
```

### Batch Operations (2 tools)

#### 7. `batch_delete_tasks`
Delete multiple tasks at once (max 100).

**Parameters:**
- `user_id` (required): User ID for authorization
- `task_ids` (required): Comma-separated task IDs (e.g., `"1,2,3,42"`)

**Security:** Maximum 100 tasks per batch operation.

#### 8. `batch_update_tasks`
Update multiple tasks with the same values (max 100).

**Parameters:**
- `user_id` (required): User ID for authorization
- `task_ids` (required): Comma-separated task IDs
- `status` (optional): New status to apply to all tasks

**Example:**
```json
{
  "user_id": 1,
  "task_ids": "1,2,3",
  "status": "completed"
}
```

### SQL Operations (2 tools)

#### 9. `generate_sql_query`
Generate SQL query from natural language question.

**Parameters:**
- `user_id` (required): User ID (included in generated query)
- `question` (required): Natural language question

**Examples:**
- `"show my tasks"` → `SELECT * FROM todos WHERE user_id = 1 ORDER BY created_at ASC`
- `"count completed tasks"` → `SELECT COUNT(*) FROM todos WHERE user_id = 1 AND status = 'completed'`
- `"list pending tasks"` → `SELECT * FROM todos WHERE user_id = 1 AND status = 'pending' ORDER BY created_at ASC`

**Note:** Returns SQL string only - does not execute it.

#### 10. `execute_sql_query`
Execute a SELECT-only SQL query (read-only).

**Parameters:**
- `user_id` (required): User ID (must be in WHERE clause)
- `query` (required): SQL SELECT query

**Security Restrictions:**
- ✅ Only `SELECT` queries allowed
- ❌ Rejects: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`
- ✅ Must include `user_id` in WHERE clause
- ✅ Parameterized queries prevent SQL injection

**Example:**
```json
{
  "user_id": 1,
  "query": "SELECT id, title, status FROM todos WHERE user_id = 1 AND status = 'pending'"
}
```

## 🔒 Security

- All queries automatically filter by `user_id`
- SQL queries are parameterized to prevent injection
- `execute_sql_query` is SELECT-only (read-only access)
- Batch operations limited to 100 items max
- SSL required for database connections

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Todos Table
```sql
CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL,
    due_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    created_by VARCHAR(255)
);
```

**Actual Schema (9 columns):**
- `id`: Auto-increment primary key
- `title`: Task title (required)
- `description`: Task description (optional)
- `status`: Task status - `pending`, `in_progress`, or `completed`
- `user_id`: Foreign key to users table (required)
- `created_at`: Creation timestamp (auto-set)
- `updated_at`: Last update timestamp (auto-updated)
- `due_date`: Optional due date
- `created_by`: Creation attribution string (format: "task created by 'username'")

## 📁 Project Structure

```
query-agent-mcp/
├── spec/                    # SLC specification files
│   ├── SPEC.md             # Entry point (Authority Level 1)
│   ├── SECURITY.md         # Security rules (Authority Level 2)
│   ├── MEMORY.md           # Decision log (Authority Level 3)
│   ├── CONSTRAINTS.md      # Technical limits (Authority Level 4)
│   ├── CONTEXT.md          # Project intent (Authority Level 5)
│   └── backend_specs/      # Implementation specs
│       ├── ARCH.md         # Architecture
│       ├── PLAN.md         # 3-phase plan
│       ├── CONTRACT.md     # API contracts
│       └── tasks/          # Individual task files
├── src/
│   └── mcp_server/
│       ├── __init__.py
│       ├── __main__.py     # Package entry point
│       ├── server.py       # MCP server implementation
│       ├── database.py     # Database connection pool
│       └── tools/          # Tool implementations
│           ├── task_tools.py
│           ├── batch_tools.py
│           └── sql_tools.py
├── .env                    # Environment configuration (not in git)
├── .env.example            # Environment template
├── pyproject.toml          # Python project configuration
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🧪 Development

### Phase 1: Foundation ✅ COMPLETED
- ✅ Project initialization
- ✅ Directory structure
- ✅ Environment configuration
- ✅ Database connection pool
- ✅ Tool module stubs
- ✅ MCP server skeleton
- ✅ Database connection testing
- ✅ Server startup testing

### Phase 2: Implementation ✅ COMPLETED
- ✅ All 10 tool implementations
- ✅ Error handling
- ✅ Input validation
- ✅ SQL query generation
- ✅ Batch operations (max 100 limit)
- ✅ Security controls (user isolation, parameterized queries)

### Phase 3: Testing & Documentation ✅ COMPLETED
- ✅ Functional testing (all tools)
- ✅ Security testing (SQL injection, user isolation, batch limits)
- ✅ Documentation
- ⏳ Integration testing (MCP client)

## 📝 Specifications

This project follows the SLC (Spec Language for Cognition) format. All specifications are in the `spec/` directory with a strict read order:

1. Read `SPEC.md` first (mandatory)
2. Follow the read order defined in SPEC.md
3. Consult `MEMORY.md` for frozen decisions
4. Respect authority hierarchy (SPEC > SECURITY > MEMORY > CONSTRAINTS > CONTEXT)

## 🧪 Testing

### Run All Tests

```bash
# Database connection test
python test_db_connection.py

# Server startup and tool registration test
python test_server_startup.py

# Functional tests (all 10 tools)
python test_tools_functional.py

# Security tests (SQL injection, user isolation, batch limits)
python test_security.py
```

### Test Coverage

**Functional Tests:**
- ✅ All 10 tools work correctly
- ✅ Optional parameters handled properly
- ✅ Filtering works (status filters)
- ✅ Batch operations (single and bulk)
- ✅ SQL generation from natural language
- ✅ SQL execution with valid queries
- ✅ Edge cases (empty arrays, non-existent tasks, etc.)

**Security Tests:**
- ✅ SQL injection prevention (parameterized queries)
- ✅ User isolation (cannot access other users' tasks)
- ✅ Batch limit enforcement (max 100 items)
- ✅ execute_sql_query restrictions (SELECT-only)
- ✅ execute_sql_query requires user_id filter
- ✅ Cross-user access prevention (get, update, delete, batch)

## 🐛 Troubleshooting

**Database connection fails:**
- Verify DATABASE_URL in `.env` is correct
- Ensure Neon database is accessible
- Check SSL mode is enabled (`sslmode=require`)
- Verify users and todos tables exist

**Server won't start:**
- Check Python version (3.11+ required)
- Install dependencies: `pip install -r requirements.txt`
- Verify virtual environment is activated
- Check for syntax errors: `python test_server_startup.py`

**Tools not appearing in client:**
- Verify MCP client configuration
- Check server is running: `python -m src.mcp_server`
- Review MCP client logs for errors
- Ensure `cwd` path in config is correct

## 📜 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This project is built following strict SLC specifications. Before contributing:

1. Read `spec/SPEC.md` in its entirety
2. Review `spec/MEMORY.md` for frozen decisions
3. Consult `spec/SECURITY.md` for security requirements
4. Follow the authority hierarchy defined in specs

## 📧 Support

For issues or questions, please open a GitHub issue.

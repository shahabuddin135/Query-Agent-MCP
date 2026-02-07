# Deployment & Usage Guide

## 🔒 Authentication & Security Model

### API Key Authentication (Streamable HTTP)

**This MCP server uses API key authentication.** Every HTTP request to the `/mcp` endpoint must include a valid `Authorization: Bearer <MCP_API_KEY>` header.

- **API key** is set via the `MCP_API_KEY` environment variable
- Server **refuses to start** if `MCP_API_KEY` is not set
- Invalid/missing keys return **401 Unauthorized**
- Uses constant-time comparison (`hmac.compare_digest`) to prevent timing attacks
- Failed auth attempts are **logged** with the client IP

### Security Model

```
┌─────────────────┐
│   MCP Client    │  ← Must send Authorization: Bearer <key>
│ (Agent / Script) │  ← Passes user_id with each request
└────────┬────────┘
         │ Authenticated HTTP + user_id
         ▼
┌─────────────────┐
│   MCP Server    │  ← API key middleware (Starlette)
│ (This Project)  │  ← Enforces user_id filtering
│                 │  ← Prevents SQL injection
│                 │  ← Table allowlist (todos only)
└────────┬────────┘
         │ Parameterized queries
         ▼
┌─────────────────┐
│  Neon Database  │  ← SSL/TLS encrypted
└─────────────────┘
```

**Security Controls:**
- ✅ **API Key Auth**: All `/mcp` requests require valid Bearer token
- ✅ **User Isolation**: All queries filter by `user_id` — users cannot access each other's data
- ✅ **SQL Injection Prevention**: Parameterized queries ($1, $2, etc.) — no f-string interpolation
- ✅ **Table Allowlist**: Only `todos` table can be queried — `users` table blocked
- ✅ **Query Chaining Blocked**: Semicolons and SQL comments rejected
- ✅ **Read-only SQL**: `execute_sql_query` only allows SELECT statements
- ✅ **Batch Limits**: Maximum 100 items per batch operation
- ✅ **Error Sanitization**: Generic error messages — no PostgreSQL internals leaked
- ✅ **SSL/TLS**: Database connections require `sslmode=require`

### Environment Setup

```bash
# Generate an API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
MCP_API_KEY=<generated-key>
```

### Client Connection (with auth)

```bash
# Example: curl with API key
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## 🚀 Local Development & Testing

### Method 1: Direct Server Testing (Stdio)

Run the server directly to test stdio communication:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Run server
python -m src.mcp_server
```

The server will:
- Start and listen on stdin/stdout
- Wait for JSON-RPC messages
- Accept tool calls via MCP protocol

**To test manually**, send JSON-RPC messages via stdin:

```json
{"jsonrpc":"2.0","method":"tools/list","id":1}
```

Expected response (via stdout):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {"name": "create_task", "description": "...", "inputSchema": {...}},
      ...
    ]
  }
}
```

### Method 2: MCP Inspector (Recommended for Local Testing)

Install the MCP Inspector:

```bash
npm install -g @modelcontextprotocol/inspector
```

Run inspector with your server:

```bash
mcp-inspector python -m src.mcp_server
```

This opens a web UI at `http://localhost:5173` where you can:
- See all 10 tools
- Test tool calls with a GUI
- View request/response JSON
- Debug errors

### Method 3: VS Code with Continue Extension

1. **Install Continue** extension in VS Code

2. **Configure Continue** (`~/.continue/config.json`):

```json
{
  "mcpServers": {
    "query-agent-mcp": {
      "command": "D:\\my-projects\\query-agent-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp_server"],
      "cwd": "D:\\my-projects\\query-agent-mcp",
      "env": {
        "DATABASE_URL": "postgresql://user:password@host/database?sslmode=require"
      }
    }
  }
}
```

3. **Reload Continue** and verify tools appear

4. **Test in chat**:
```
@query-agent-mcp create a task for user 1 with title "Test from VS Code"
```

### Method 4: Custom Test Client

Create a simple test script:

```python
# test_client.py
import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp_server"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            for tool in tools.tools:
                print(f"  - {tool.name}")
            
            # Call create_task
            result = await session.call_tool(
                "create_task",
                arguments={
                    "user_id": 1,
                    "title": "Test task from client",
                    "description": "Testing MCP client"
                }
            )
            print(f"\nResult: {result.content}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
```

Run:
```bash
pip install mcp
python test_client.py
```

---

## 🏗️ Production Deployment

### Option 1: Vercel (Recommended)

**Use case**: Serverless deployment — zero infrastructure management, auto-scaling

The server uses `stateless_http=True`, making every request independent — fully compatible with Vercel's serverless model.

**Prerequisites**: [Vercel CLI](https://vercel.com/docs/cli) installed (`npm i -g vercel`)

```bash
# 1. Deploy to Vercel
vercel

# 2. Set environment variables (Vercel dashboard → Settings → Environment Variables)
#    DATABASE_URL = postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require
#    MCP_API_KEY  = <your-api-key>

# 3. Production deploy
vercel --prod
```

Your MCP endpoint: `https://your-project.vercel.app/mcp`

**How it works**:
- `vercel.json` routes all requests to `api/index.py`
- `api/index.py` imports the ASGI `app` from `src/mcp_server/server.py`
- Vercel's `@vercel/python` runtime serves it as a serverless function
- API key middleware runs on every request before reaching MCP handler

**Test the deployment**:
```bash
curl -X POST https://your-project.vercel.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### Option 2: Docker Deployment

**Use case**: Self-hosted, full control over infrastructure

```bash
docker build -t query-agent-mcp .
docker run -d --name mcp-server \
  -e DATABASE_URL="postgresql://..." \
  -e MCP_API_KEY="your-secure-key-here" \
  -p 8000:8000 \
  query-agent-mcp
```

**Docker Compose** (multi-user):

```yaml
version: '3.8'
services:
  mcp-user1:
    build: .
    environment:
      - DATABASE_URL=${USER1_DB_URL}
      - MCP_API_KEY=${USER1_API_KEY}
    ports:
      - "8001:8000"
    restart: always
  
  mcp-user2:
    build: .
    environment:
      - DATABASE_URL=${USER2_DB_URL}
      - MCP_API_KEY=${USER2_API_KEY}
    ports:
      - "8002:8000"
    restart: always
```

---

## 📡 Usage with MCP Clients

### Claude Desktop

**Config location**: 
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Configuration**:
```json
{
  "mcpServers": {
    "query-agent-mcp": {
      "command": "D:\\my-projects\\query-agent-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp_server"],
      "cwd": "D:\\my-projects\\query-agent-mcp"
    }
  }
}
```

**Usage**:
```
User: Create a task for user 1 to "Buy groceries"
Claude: [calls create_task tool]
Result: ✅ Created task #42: 'Buy groceries'
```

### Continue (VS Code)

**Config location**: `~/.continue/config.json`

**Configuration**: Same as Claude Desktop

**Usage**:
```
@query-agent-mcp list all pending tasks for user 1
```

### Cline (VS Code)

**Configuration**: Add to Cline settings

**Usage**: Similar to Continue

### Custom Integration

Use the MCP Python SDK:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_mcp_server():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp_server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Use the server
            result = await session.call_tool("list_tasks", {
                "user_id": 1,
                "status": "pending"
            })
```

---

## 🔧 Configuration Best Practices

### Environment Variables

**Development** (`.env`):
```bash
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/dev_db?sslmode=require
MCP_API_KEY=your-dev-api-key-at-least-32-chars-long
```

**Production** (System environment):
```bash
# Linux/macOS
export DATABASE_URL="postgresql://prod_user:prod_pass@prod.neon.tech/prod_db?sslmode=require"
export MCP_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Windows
set DATABASE_URL=postgresql://prod_user:prod_pass@prod.neon.tech/prod_db?sslmode=require
set MCP_API_KEY=your-production-api-key
```

**Vercel** (via dashboard → Settings → Environment Variables):
```
DATABASE_URL=<your connection string>
MCP_API_KEY=<your API key>
```

### Database Connection Pool

Current defaults (in `database.py`):
- `min_size=1`: Minimum 1 connection always available
- `max_size=10`: Maximum 10 concurrent connections
- `command_timeout=30`: 30-second query timeout

**Adjust for production**:

```python
# For high-traffic production
pool = await asyncpg.create_pool(
    database_url,
    min_size=5,      # More warm connections
    max_size=50,     # Handle more concurrent users
    command_timeout=60  # Longer timeout for complex queries
)
```

### Security Hardening

1. **API Key**:
   - Generate a strong key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Rotate keys periodically
   - Never commit keys to version control
   - Use different keys per environment (dev/staging/prod)

2. **Database Credentials**:
   - Never commit `.env` to git (already in `.gitignore`)
   - Use environment variables or secrets manager
   - Rotate credentials regularly

3. **SSL/TLS**:
   - Always use `sslmode=require` in DATABASE_URL
   - Neon enforces SSL by default

4. **Network Security**:
   - MCP server listens on Streamable HTTP (configurable host/port)
   - API key protects the endpoint from unauthorized access
   - Database connection uses SSL/TLS
   - Use Neon IP allowlist if available
   - Consider reverse proxy (nginx) for TLS termination in production

4. **Logging** (add to production):
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   # Log all tool calls (add to handle_call_tool)
   logger.info(f"Tool call: {name} by user {arguments.get('user_id')}")
   ```

---

## 🎯 Quick Start Checklist

**For Local VS Code Testing:**

- [x] Virtual environment activated
- [x] Dependencies installed (`pip install -r requirements.txt`)
- [x] `.env` configured with DATABASE_URL
- [x] Database connection tested (`python test_db_connection.py`)
- [x] Server startup tested (`python test_server_startup.py`)
- [ ] MCP Inspector installed (`npm install -g @modelcontextprotocol/inspector`)
- [ ] Run inspector: `mcp-inspector python -m src.mcp_server`
- [ ] Test tools in web UI at `http://localhost:5173`

**For Production Deployment (Vercel):**

- [ ] Vercel CLI installed (`npm i -g vercel`)
- [ ] Project linked (`vercel`)
- [ ] `DATABASE_URL` set in Vercel dashboard
- [ ] `MCP_API_KEY` set in Vercel dashboard
- [ ] Production deploy done (`vercel --prod`)
- [ ] Test endpoint: `curl https://your-project.vercel.app/mcp`
- [ ] Monitoring set up (Vercel dashboard logs)

---

## 🐛 Troubleshooting

### Server won't start

```bash
# Check Python version
python --version  # Must be 3.11+

# Test imports
python -c "import src.mcp_server; print('OK')"

# Check database URL
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DATABASE_URL'))"
```

### Database connection errors

```bash
# Test connection directly
python test_db_connection.py

# Check SSL mode
# Must include: ?sslmode=require

# Verify Neon database is accessible
ping <neon-host>.neon.tech
```

### Tools not working

```bash
# Run functional tests
python test_tools_functional.py

# Check specific tool
python -c "
from src.mcp_server.tools import task_tools
import asyncio
from dotenv import load_dotenv
load_dotenv()
from src.mcp_server.database import get_db_pool
async def test():
    pool = await get_db_pool()
    result = await task_tools.list_tasks(pool, user_id=1)
    print(result)
asyncio.run(test())
"
```

### Permission issues

```bash
# Verify user exists in database
python -c "
import asyncio
from dotenv import load_dotenv
load_dotenv()
from src.mcp_server.database import get_db_pool
async def check():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch('SELECT id, username FROM users')
        for u in users:
            print(f'User {u[\"id\"]}: {u[\"username\"]}')
asyncio.run(check())
"
```

---

## 📊 Monitoring & Maintenance

### Health Checks

Create `health_check.py`:

```python
import asyncio
from src.mcp_server.database import get_db_pool, close_db_pool

async def health_check():
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        await close_db_pool()
        return True
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(health_check())
    exit(0 if success else 1)
```

Run periodically:
```bash
# Linux cron (every 5 minutes)
*/5 * * * * cd /opt/query-agent-mcp && .venv/bin/python health_check.py || systemctl restart query-agent-mcp
```

### Performance Monitoring

Monitor these metrics:
- Database connection pool usage
- Query execution times
- Tool call frequency per user
- Error rates

Add to `server.py`:
```python
import time

# In handle_call_tool
start_time = time.time()
# ... execute tool ...
duration = time.time() - start_time
logger.info(f"Tool {name} completed in {duration:.3f}s")
```

### Database Maintenance

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'your_db_name';

-- Vacuum tables (Neon does this automatically, but can be run manually)
VACUUM ANALYZE todos;
VACUUM ANALYZE users;
```

---

## 🚀 Next Steps

1. **Test locally** with MCP Inspector
2. **Integrate** with your preferred MCP client
3. **Deploy** to Vercel (`vercel --prod`)
4. **Monitor** performance and errors
5. **Scale** — Vercel handles auto-scaling automatically

**Remember**: This server requires API key authentication via `Authorization: Bearer <MCP_API_KEY>` header on all requests. Generate a key with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and set `MCP_API_KEY` in your environment.

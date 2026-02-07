# Quick Start

## 1. Clone & Install

```bash
git clone https://github.com/shahabuddin135/Query-Agent-MCP.git
cd Query-Agent-MCP
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your **Neon database URL**:

```dotenv
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
```

## 3. Generate API Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and add it to `.env`:

```dotenv
MCP_API_KEY=<paste-generated-key-here>
```

## 4. Start the Server

```bash
python -m src.mcp_server
```

You should see:

```
MCP endpoint: http://0.0.0.0:8000/mcp
API key authentication: ENABLED
Uvicorn running on http://0.0.0.0:8000
```

Use a custom port:

```bash
# Windows PowerShell
$env:PORT="8001"; python -m src.mcp_server

# Linux/macOS
PORT=8001 python -m src.mcp_server
```

## 5. Test It

**No key → 401:**

```bash
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":1,\"params\":{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}"
```

**With key → 200:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":1,\"params\":{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}"
```

## 6. MCP Inspector (GUI Testing)

```bash
npm install -g @modelcontextprotocol/inspector
npx @modelcontextprotocol/inspector
```

Open `http://localhost:5173`, set:
- **Transport**: Streamable HTTP
- **URL**: `http://localhost:8000/mcp`
- **Headers**: `Authorization: Bearer <your-api-key>`

## 7. Connect from Code

```python
import httpx, json

API_KEY = "your-api-key"
URL = "http://localhost:8000/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

# Initialize
resp = httpx.post(URL, headers=HEADERS, json={
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {},
               "clientInfo": {"name": "agent", "version": "1.0"}}
})
session_id = resp.headers.get("mcp-session-id")

# List tools
resp = httpx.post(URL, headers={**HEADERS, "Mcp-Session-Id": session_id},
                  json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
print(json.dumps(resp.json(), indent=2))

# Call a tool
resp = httpx.post(URL, headers={**HEADERS, "Mcp-Session-Id": session_id},
                  json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "list_tasks",
                                   "arguments": {"user_id": 1}}})
print(json.dumps(resp.json(), indent=2))
```

## 8. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy (first time — will prompt to link project)
vercel

# Set environment variables in Vercel dashboard:
#   DATABASE_URL = postgresql://user:pass@host/db?sslmode=require
#   MCP_API_KEY  = <your-generated-key>

# Production deploy
vercel --prod
```

Your MCP endpoint will be at: `https://your-project.vercel.app/mcp`

## Available Tools

| Tool | Description |
|------|-------------|
| `create_task` | Create a new task |
| `list_tasks` | List tasks (optional status filter) |
| `update_task` | Update title/description/status/due_date |
| `delete_task` | Delete a task |
| `get_task_details` | Get full task details |
| `search_tasks_by_keyword` | Search by keyword |
| `batch_delete_tasks` | Delete multiple tasks (max 100) |
| `batch_update_tasks` | Update multiple tasks (max 100) |
| `generate_sql_query` | Generate SQL from natural language |
| `execute_sql_query` | Execute read-only SQL (SELECT only) |

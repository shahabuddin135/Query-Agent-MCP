# AI Agent Integration Guide

## 🎯 Overview

This guide explains how to integrate the Query Agent MCP Server into your AI agent project, where to host it, and how your agent will communicate with it.

## 🏗️ Architecture

### How MCP Fits Into Your AI Agent

```
┌─────────────────────────────────────────────────────┐
│              YOUR AI AGENT APPLICATION              │
│                                                     │
│  ┌──────────────┐         ┌──────────────┐        │
│  │   LLM Core   │────────▶│ MCP Client   │        │
│  │ (Claude API, │         │   (stdio)    │        │
│  │  OpenAI, etc)│         └──────┬───────┘        │
│  └──────────────┘                │                 │
│                                   │                 │
└───────────────────────────────────┼─────────────────┘
                                    │ stdio (stdin/stdout)
                                    │ JSON-RPC 2.0
                                    ▼
         ┌──────────────────────────────────┐
         │   Query Agent MCP Server         │
         │   (This Project)                 │
         │                                  │
         │  ┌────────┐  ┌────────┐         │
         │  │ Task   │  │ Batch  │         │
         │  │ Tools  │  │ Tools  │         │
         │  └───┬────┘  └───┬────┘         │
         │      └────┬───────┘              │
         │           ▼                      │
         │   ┌──────────────┐              │
         │   │ asyncpg Pool │              │
         │   └──────┬───────┘              │
         └──────────┼──────────────────────┘
                    │ PostgreSQL Protocol
                    ▼
         ┌──────────────────┐
         │  Neon Database   │
         │  (PostgreSQL)    │
         └──────────────────┘
```

### Communication Flow

1. **User Request** → AI Agent receives natural language query
2. **Agent Decision** → LLM decides which MCP tool(s) to call
3. **MCP Call** → Agent sends JSON-RPC request via stdio
4. **Tool Execution** → MCP server executes database operations
5. **Result** → Server returns JSON response via stdout
6. **Agent Response** → LLM formats result for user

---

## 🌐 Hosting Options

### Option 1: Local Development (Same Machine)

**Best for:** Development, testing, single-user prototypes

```
┌──────────────────────────────────┐
│     Your Development Machine     │
│                                  │
│  ┌──────────────┐               │
│  │  AI Agent    │               │
│  │  Process     │               │
│  └──────┬───────┘               │
│         │ stdio                  │
│         ▼                        │
│  ┌──────────────┐               │
│  │  MCP Server  │               │
│  │  (subprocess)│               │
│  └──────┬───────┘               │
└─────────┼────────────────────────┘
          │ Network
          ▼
   ┌──────────────┐
   │Neon Database │
   │   (Cloud)    │
   └──────────────┘
```

**Setup:**

```python
# Your AI agent launches MCP server as subprocess
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def init_mcp():
    server_params = StdioServerParameters(
        command="D:\\my-projects\\query-agent-mcp\\.venv\\Scripts\\python.exe",
        args=["-m", "src.mcp_server"],
        cwd="D:\\my-projects\\query-agent-mcp",
        env={"DATABASE_URL": "postgresql://..."}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return session
```

**Pros:**
- ✅ Simple setup
- ✅ Fast (no network latency)
- ✅ Easy debugging

**Cons:**
- ❌ Doesn't scale
- ❌ Single point of failure
- ❌ Not suitable for production multi-user

---

### Option 2: Separate Process (Same Server)

**Best for:** Production single-user, better isolation

```
┌──────────────────────────────────┐
│      Your Production Server      │
│                                  │
│  ┌──────────────┐               │
│  │  AI Agent    │               │
│  │  (systemd)   │               │
│  └──────┬───────┘               │
│         │ stdio/IPC              │
│         ▼                        │
│  ┌──────────────┐               │
│  │  MCP Server  │               │
│  │  (systemd)   │               │
│  └──────┬───────┘               │
└─────────┼────────────────────────┘
          │
          ▼
   Neon Database
```

**Setup (Linux systemd):**

```ini
# /etc/systemd/system/mcp-server.service
[Unit]
Description=Query Agent MCP Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/opt/query-agent-mcp
Environment="PATH=/opt/query-agent-mcp/.venv/bin"
Environment="DATABASE_URL=postgresql://..."
ExecStart=/opt/query-agent-mcp/.venv/bin/python -m src.mcp_server
StandardInput=socket
StandardOutput=socket
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/ai-agent.service
[Unit]
Description=AI Agent Application
After=mcp-server.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/opt/ai-agent
ExecStart=/opt/ai-agent/.venv/bin/python main.py
Environment="MCP_SERVER_COMMAND=python -m src.mcp_server"
Restart=always
```

---

### Option 3: Containerized (Docker)

**Best for:** Multi-user, cloud deployment, scalability

```
┌──────────────────────────────────────┐
│        Your Cloud/Server             │
│                                      │
│  ┌────────────────────┐             │
│  │  AI Agent Container│             │
│  │  (Docker)          │             │
│  └────────┬───────────┘             │
│           │ stdio                    │
│           ▼                          │
│  ┌────────────────────┐             │
│  │  MCP Server        │             │
│  │  Container (Docker)│             │
│  └────────┬───────────┘             │
└───────────┼──────────────────────────┘
            │
            ▼
     Neon Database
```

**Docker Compose:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-server:
    build:
      context: ./query-agent-mcp
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
    stdin_open: true
    tty: true
    restart: always
    networks:
      - agent-network

  ai-agent:
    build:
      context: ./ai-agent
      dockerfile: Dockerfile
    depends_on:
      - mcp-server
    environment:
      - MCP_SERVER_HOST=mcp-server
    networks:
      - agent-network
    ports:
      - "8000:8000"

networks:
  agent-network:
    driver: bridge
```

**MCP Server Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Run server
CMD ["python", "-m", "src.mcp_server"]
```

---

### Option 4: Multi-Instance (User Isolation)

**Best for:** SaaS applications, true multi-tenant

```
┌────────────────────────────────────────┐
│          Load Balancer / Proxy         │
└────────┬───────────────────────────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐
│Agent + │ │Agent + │ │Agent + │
│MCP     │ │MCP     │ │MCP     │
│User 1  │ │User 2  │ │User N  │
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     └──────────┴──────────┘
                │
                ▼
         Neon Database
         (Row-level security)
```

---

## 💻 Development Workflow

### Project Structure

```
your-ai-agent-project/
├── ai-agent/                    # Your AI agent code
│   ├── main.py                 # Agent entry point
│   ├── mcp_client.py           # MCP client wrapper
│   ├── llm_integration.py      # LLM (Claude/GPT) integration
│   └── requirements.txt
├── query-agent-mcp/            # This MCP server (submodule/separate repo)
│   ├── src/
│   │   └── mcp_server/
│   ├── .env
│   └── requirements.txt
└── docker-compose.yml          # Optional: for containerized deployment
```

### Step 1: Clone/Include MCP Server

**Option A: Git Submodule**
```bash
cd your-ai-agent-project
git submodule add https://github.com/you/query-agent-mcp.git
cd query-agent-mcp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Option B: Direct Clone**
```bash
cd your-ai-agent-project
git clone https://github.com/you/query-agent-mcp.git
# Setup same as above
```

### Step 2: Configure Environment

```bash
# query-agent-mcp/.env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
```

### Step 3: Create MCP Client Wrapper

```python
# ai-agent/mcp_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional, Dict, Any
import json

class TaskMCPClient:
    """MCP client for task management operations."""
    
    def __init__(self, server_path: str = "../query-agent-mcp"):
        self.server_path = server_path
        self.session: Optional[ClientSession] = None
        
    async def __aenter__(self):
        """Start MCP server and initialize session."""
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "src.mcp_server"],
            cwd=self.server_path
        )
        
        self.client = stdio_client(server_params)
        self.read, self.write = await self.client.__aenter__()
        
        self.session = ClientSession(self.read, self.write)
        await self.session.__aenter__()
        await self.session.initialize()
        
        return self
        
    async def __aexit__(self, *args):
        """Cleanup session and server."""
        if self.session:
            await self.session.__aexit__(*args)
        await self.client.__aexit__(*args)
    
    async def create_task(
        self,
        user_id: int,
        title: str,
        description: str = "",
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new task."""
        result = await self.session.call_tool(
            "create_task",
            arguments={
                "user_id": user_id,
                "title": title,
                "description": description,
                "due_date": due_date
            }
        )
        return json.loads(result.content[0].text)
    
    async def list_tasks(
        self,
        user_id: int,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List tasks with optional status filter."""
        result = await self.session.call_tool(
            "list_tasks",
            arguments={
                "user_id": user_id,
                "status": status
            }
        )
        return json.loads(result.content[0].text)
    
    async def execute_sql_query(
        self,
        user_id: int,
        query: str
    ) -> Dict[str, Any]:
        """Execute a SELECT query."""
        result = await self.session.call_tool(
            "execute_sql_query",
            arguments={
                "user_id": user_id,
                "query": query
            }
        )
        return json.loads(result.content[0].text)
```

### Step 4: Integrate with Your AI Agent

```python
# ai-agent/main.py
import asyncio
from mcp_client import TaskMCPClient
from llm_integration import call_llm  # Your LLM wrapper

async def handle_user_request(user_id: int, user_message: str):
    """Process user request with LLM + MCP tools."""
    
    async with TaskMCPClient() as mcp:
        # Step 1: Get available tools
        tools = await mcp.session.list_tools()
        
        # Step 2: Call LLM with tools available
        response = await call_llm(
            message=user_message,
            tools=[tool.model_dump() for tool in tools.tools]
        )
        
        # Step 3: Execute tool calls if LLM requests them
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.name == "create_task":
                    result = await mcp.create_task(
                        user_id=user_id,
                        **tool_call.arguments
                    )
                    print(f"Created task: {result}")
                
                elif tool_call.name == "list_tasks":
                    result = await mcp.list_tasks(
                        user_id=user_id,
                        **tool_call.arguments
                    )
                    print(f"Found {len(result.get('tasks', []))} tasks")
                
                # ... handle other tools
        
        return response

# Example usage
async def main():
    user_id = 1
    
    # User asks agent to create a task
    await handle_user_request(
        user_id=user_id,
        user_message="Create a task to review PR #123 by tomorrow"
    )
    
    # User asks agent to list tasks
    await handle_user_request(
        user_id=user_id,
        user_message="What are my pending tasks?"
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 5: LLM Integration Example (Anthropic Claude)

```python
# ai-agent/llm_integration.py
from anthropic import Anthropic
import os

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def call_llm(message: str, tools: list):
    """Call Claude with MCP tools available."""
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=tools,
        messages=[{
            "role": "user",
            "content": message
        }]
    )
    
    # Extract tool calls
    tool_calls = []
    for block in response.content:
        if block.type == "tool_use":
            tool_calls.append({
                "name": block.name,
                "arguments": block.input
            })
    
    return {
        "text": response.content[0].text if response.content else "",
        "tool_calls": tool_calls
    }
```

### Step 6: OpenAI Integration Example

```python
# ai-agent/llm_integration_openai.py
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def call_llm(message: str, tools: list):
    """Call GPT with MCP tools available."""
    
    # Convert MCP tool schema to OpenAI format
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        })
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": message}],
        tools=openai_tools,
        tool_choice="auto"
    )
    
    # Extract tool calls
    tool_calls = []
    if response.choices[0].message.tool_calls:
        for call in response.choices[0].message.tool_calls:
            tool_calls.append({
                "name": call.function.name,
                "arguments": json.loads(call.function.arguments)
            })
    
    return {
        "text": response.choices[0].message.content or "",
        "tool_calls": tool_calls
    }
```

---

## 🚀 Deployment Strategies

### Strategy 1: Development (Local)

```bash
# Terminal 1: Start MCP server manually
cd query-agent-mcp
.venv\Scripts\activate
python -m src.mcp_server

# Terminal 2: Run your AI agent
cd ai-agent
.venv\Scripts\activate
python main.py
```

### Strategy 2: Production (Docker Compose)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f ai-agent
docker-compose logs -f mcp-server

# Scale for multiple users
docker-compose up -d --scale mcp-server=3
```

### Strategy 3: Cloud (AWS/GCP/Azure)

**AWS Example:**

1. **Deploy MCP Server** on ECS Fargate
2. **Deploy AI Agent** on ECS or Lambda
3. **Use Systems Manager Parameter Store** for DATABASE_URL
4. **Connect via VPC** for secure communication

**Configuration:**

```bash
# Store secrets
aws ssm put-parameter \
  --name /mcp/database-url \
  --value "postgresql://..." \
  --type SecureString

# ECS Task Definition
{
  "containerDefinitions": [
    {
      "name": "mcp-server",
      "image": "your-registry/query-agent-mcp:latest",
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "/mcp/database-url"
        }
      ]
    }
  ]
}
```

---

## 🔧 Configuration Best Practices

### Environment Management

```python
# ai-agent/.env.development
MCP_SERVER_PATH=../query-agent-mcp
DATABASE_URL=postgresql://dev@localhost/dev_db?sslmode=require
ANTHROPIC_API_KEY=sk-ant-...

# ai-agent/.env.production
MCP_SERVER_PATH=/opt/query-agent-mcp
DATABASE_URL=postgresql://prod@prod.neon.tech/prod_db?sslmode=require
ANTHROPIC_API_KEY=sk-ant-prod-...
```

### User Management

```python
# Map your application users to MCP user_ids
class UserContext:
    def __init__(self, app_user_id: str):
        self.app_user_id = app_user_id
        # Map to database user_id
        self.mcp_user_id = self.get_mcp_user_id(app_user_id)
    
    def get_mcp_user_id(self, app_user_id: str) -> int:
        # Lookup or create mapping
        # Could be stored in Redis, database, etc.
        return user_id_mapping.get(app_user_id, 1)
```

### Error Handling

```python
async def safe_mcp_call(mcp_client, tool_name, **kwargs):
    """Wrapper for MCP calls with error handling."""
    try:
        result = await mcp_client.session.call_tool(tool_name, kwargs)
        data = json.loads(result.content[0].text)
        
        if data.get("success") is False:
            raise ValueError(data.get("error", "Unknown error"))
        
        return data
        
    except Exception as e:
        print(f"MCP call failed: {tool_name} - {e}")
        # Fallback or retry logic
        return {"success": False, "error": str(e)}
```

---

## 📊 Monitoring & Logging

### Application Logging

```python
# ai-agent/logging_config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# In your code
logger.info(f"User {user_id} created task via MCP")
logger.error(f"MCP call failed: {error}")
```

### Metrics Tracking

```python
from prometheus_client import Counter, Histogram

# Define metrics
mcp_calls_total = Counter('mcp_calls_total', 'Total MCP calls', ['tool_name'])
mcp_duration = Histogram('mcp_call_duration_seconds', 'MCP call duration', ['tool_name'])

# Track calls
with mcp_duration.labels(tool_name="create_task").time():
    result = await mcp.create_task(...)
mcp_calls_total.labels(tool_name="create_task").inc()
```

---

## 🎯 Example Use Cases

### Use Case 1: Task Management Agent

```python
# User: "Create 3 tasks for the new feature"
async def create_feature_tasks(user_id: int, feature_name: str):
    async with TaskMCPClient() as mcp:
        tasks = [
            {"title": f"Design {feature_name}", "description": "Create mockups"},
            {"title": f"Implement {feature_name}", "description": "Write code"},
            {"title": f"Test {feature_name}", "description": "QA testing"}
        ]
        
        results = []
        for task in tasks:
            result = await mcp.create_task(
                user_id=user_id,
                title=task["title"],
                description=task["description"]
            )
            results.append(result)
        
        return results
```

### Use Case 2: Daily Standup Assistant

```python
# User: "What did I work on yesterday?"
async def daily_standup(user_id: int):
    async with TaskMCPClient() as mcp:
        # Get completed tasks from yesterday
        query = """
        SELECT title, updated_at 
        FROM todos 
        WHERE user_id = $1 
          AND status = 'completed'
          AND DATE(updated_at) = CURRENT_DATE - 1
        ORDER BY updated_at DESC
        """
        
        result = await mcp.execute_sql_query(user_id=user_id, query=query)
        
        if result["success"]:
            tasks = result["results"]
            summary = f"Yesterday you completed {len(tasks)} tasks:\n"
            for task in tasks:
                summary += f"- {task['title']}\n"
            return summary
        else:
            return "No tasks completed yesterday"
```

### Use Case 3: Smart Batch Operations

```python
# User: "Mark all my urgent tasks as in-progress"
async def bulk_status_update(user_id: int):
    async with TaskMCPClient() as mcp:
        # First, find urgent tasks
        urgent_tasks = await mcp.list_tasks(
            user_id=user_id,
            status="pending"
        )
        
        # Filter by title containing "urgent" (case-insensitive)
        task_ids = [
            task["id"] for task in urgent_tasks.get("tasks", [])
            if "urgent" in task["title"].lower()
        ]
        
        # Batch update
        result = await mcp.session.call_tool(
            "batch_update_tasks",
            arguments={
                "user_id": user_id,
                "task_ids": task_ids,
                "status": "in-progress"
            }
        )
        
        return json.loads(result.content[0].text)
```

---

## 📋 Quick Start Checklist

- [ ] Clone/include query-agent-mcp in your project
- [ ] Set up .env with DATABASE_URL
- [ ] Install dependencies: `pip install mcp anthropic` (or openai)
- [ ] Create MCP client wrapper (mcp_client.py)
- [ ] Integrate with your LLM (Claude/GPT)
- [ ] Test locally with MCP Inspector
- [ ] Deploy MCP server (Docker/systemd/cloud)
- [ ] Configure production environment variables
- [ ] Set up monitoring and logging
- [ ] Test end-to-end user workflows

---

## 🐛 Troubleshooting

### Problem: Agent can't connect to MCP server

```python
# Check if server is running
import subprocess
result = subprocess.run(
    ["python", "-m", "src.mcp_server"],
    cwd="../query-agent-mcp",
    capture_output=True,
    text=True,
    timeout=5
)
print(result.stderr)
```

### Problem: Tool calls failing

```python
# Enable debug logging
import logging
logging.getLogger("mcp").setLevel(logging.DEBUG)

# Test direct tool call
async with TaskMCPClient() as mcp:
    tools = await mcp.session.list_tools()
    print(f"Available tools: {[t.name for t in tools.tools]}")
```

### Problem: Database connection errors

```bash
# Test database connectivity from MCP server
cd query-agent-mcp
.venv\Scripts\activate
python test_db_connection.py
```

---

## 📚 Additional Resources

- [MCP Python SDK Documentation](https://modelcontextprotocol.io/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs)
- [Neon Database Docs](https://neon.tech/docs)

---

## 🎓 Next Steps

1. **Start Simple**: Run locally with MCP Inspector to understand the flow
2. **Build Your Agent**: Integrate with your LLM of choice
3. **Test Thoroughly**: Use all 10 tools in various scenarios
4. **Deploy Incrementally**: Start with single-user, scale as needed
5. **Monitor Performance**: Track usage, errors, and optimize

**Your MCP server is ready to power intelligent task management in your AI agent! 🚀**

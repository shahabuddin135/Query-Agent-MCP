# CONTRACT.md — API Contracts

> **Authority: Level 8**
> Defines authoritative API contracts for all MCP tools.
> This is the source of truth for tool interfaces.

---

```slc
@block CONTRACT overview
priority: critical
intent: "MCP tool API contracts"
scope: global
depends_on: [ARCH.tool_schemas]

content:
  protocol: "Model Context Protocol (MCP)"
  transport: "stdio (JSON-RPC 2.0)"
  tool_count: 10
  
  contract_principles:
    - "All tool signatures are immutable once defined"
    - "All tools return structured dicts (success/error)"
    - "All tools receive context dict {user_id, db_pool}"
    - "All tools are async functions"
@end
```

---

## TOOL CONTRACTS

### Task Management Tools (6)

```slc
@block CONTRACT tool_create_task
priority: critical
intent: "create_task API contract"
scope: global

content:
  name: "create_task"
  category: "task_management"
  module: "task_tools.py"
  
  signature: |
    async def create_task(
        context: dict,
        title: str,
        description: str = "",
        due_date: Optional[str] = None
    ) -> dict
    
  parameters:
    context:
      type: "dict"
      required: true
      structure:
        user_id: "int"
        db_pool: "asyncpg.Pool"
        
    title:
      type: "str"
      required: true
      constraints: "1-255 characters, non-empty"
      
    description:
      type: "str"
      required: false
      default: '""'
      constraints: "0-1000 characters"
      
    due_date:
      type: "Optional[str]"
      required: false
      default: "None"
      format: "ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
      
  returns:
    success_response:
      success: true
      task_id: "int — ID of created task"
      message: "str — e.g., '✅ Created task #42: Title'"
      
    error_response:
      error: "str — Error message"
      
  behavior:
    - "Fetch username from users table for created_by"
    - "Format created_by as 'task created by \\'username\\' ' "
    - "Insert into todos with user_id filter"
    - "Return task ID and success message"
    
  example:
    request: |
      {
        "name": "create_task",
        "arguments": {
          "title": "Buy groceries",
          "description": "Milk, eggs, bread",
          "due_date": "2026-02-08"
        },
        "_meta": {"userId": 1}
      }
      
    response: |
      {
        "success": true,
        "task_id": 42,
        "message": "✅ Created task #42: 'Buy groceries'"
      }
@end
```

```slc
@block CONTRACT tool_list_tasks
priority: critical
intent: "list_tasks API contract"
scope: global

content:
  name: "list_tasks"
  category: "task_management"
  module: "task_tools.py"
  
  signature: |
    async def list_tasks(
        context: dict,
        status: str = "all"
    ) -> dict
    
  parameters:
    status:
      type: "str"
      required: false
      default: '"all"'
      allowed_values: ["all", "pending", "completed"]
      
  returns:
    success_response:
      success: true
      count: "int — Number of tasks"
      tasks: "list[dict] — Array of task objects"
      
  task_object_schema:
    id: "int"
    title: "str"
    description: "str | None"
    status: "str ('pending' or 'completed')"
    due_date: "datetime | None"
    created_by: "str"
    created_at: "datetime"
    updated_at: "datetime | None"
    
  behavior:
    - "Filter by user_id"
    - "Filter by status if not 'all'"
    - "ORDER BY created_at ASC (oldest first)"
    - "Return all fields for each task"
    
  example:
    request: |
      {"name": "list_tasks", "arguments": {"status": "pending"}}
      
    response: |
      {
        "success": true,
        "count": 2,
        "tasks": [
          {
            "id": 1,
            "title": "Task 1",
            "status": "pending",
            ...
          },
          {
            "id": 2,
            "title": "Task 2",
            "status": "pending",
            ...
          }
        ]
      }
@end
```

```slc
@block CONTRACT tool_update_task
priority: critical
intent: "update_task API contract"
scope: global

content:
  name: "update_task"
  category: "task_management"
  module: "task_tools.py"
  
  signature: |
    async def update_task(
        context: dict,
        task_id: int,
        title: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> dict
    
  parameters:
    task_id:
      type: "int"
      required: true
      
    title:
      type: "Optional[str]"
      required: false
      
    status:
      type: "Optional[str]"
      required: false
      allowed_values: ["pending", "completed"]
      
    description:
      type: "Optional[str]"
      required: false
      
    due_date:
      type: "Optional[str]"
      required: false
      special_values: ["none" → NULL]
      
  returns:
    success_response:
      success: true
      task: "dict — Updated task object"
      message: "str — e.g., '✅ Updated task #42'"
      
    error_response:
      error: "str — Error message"
      
  behavior:
    - "Build dynamic UPDATE query (only specified fields)"
    - "Auto-set updated_at = NOW()"
    - "At least one field required"
    - "due_date='none' sets to NULL"
    - "Filter by task_id AND user_id"
    
  example:
    request: |
      {
        "name": "update_task",
        "arguments": {
          "task_id": 42,
          "status": "completed"
        }
      }
      
    response: |
      {
        "success": true,
        "task": {...},
        "message": "✅ Updated task #42"
      }
@end
```

```slc
@block CONTRACT tool_delete_task
priority: high
intent: "delete_task API contract"
scope: global

content:
  name: "delete_task"
  category: "task_management"
  module: "task_tools.py"
  
  signature: |
    async def delete_task(
        context: dict,
        task_id: int
    ) -> dict
    
  parameters:
    task_id:
      type: "int"
      required: true
      
  returns:
    success_response:
      success: true
      message: "str — e.g., '✅ Deleted task #42: Title'"
      
    error_response:
      error: "str — e.g., '❌ Task #42 not found'"
      
  behavior:
    - "DELETE WHERE id = task_id AND user_id = context['user_id']"
    - "Return error if no rows deleted"
@end
```

```slc
@block CONTRACT tool_get_task_details
priority: medium
intent: "get_task_details API contract"
scope: global

content:
  name: "get_task_details"
  category: "task_management"
  module: "task_tools.py"
  
  signature: |
    async def get_task_details(
        context: dict,
        task_id: int
    ) -> dict
    
  parameters:
    task_id:
      type: "int"
      required: true
      
  returns:
    success_response:
      success: true
      task: "dict — Full task object with all fields"
      
    error_response:
      error: "str — e.g., '❌ Task #42 not found'"
@end
```

```slc
@block CONTRACT tool_search_tasks
priority: medium
intent: "search_tasks_by_keyword API contract"
scope: global

content:
  name: "search_tasks_by_keyword"
  category: "task_management"
  module: "task_tools.py"
  
  signature: |
    async def search_tasks_by_keyword(
        context: dict,
        keyword: str
    ) -> dict
    
  parameters:
    keyword:
      type: "str"
      required: true
      
  returns:
    success_response:
      success: true
      count: "int"
      tasks: "list[dict]"
      keyword: "str — Echo of search term"
      
  behavior:
    - "Search with PostgreSQL ILIKE: '%keyword%'"
    - "Search in title OR description"
    - "Filter by user_id"
    - "ORDER BY created_at DESC (newest first for search results)"
@end
```

---

### Batch Operation Tools (2)

```slc
@block CONTRACT tool_batch_delete
priority: critical
intent: "batch_delete_tasks API contract"
scope: global

content:
  name: "batch_delete_tasks"
  category: "batch_operations"
  module: "batch_tools.py"
  
  signature: |
    async def batch_delete_tasks(
        context: dict,
        task_ids: str
    ) -> dict
    
  parameters:
    task_ids:
      type: "str"
      required: true
      format: "comma-separated integers"
      example: "1,2,3,42,100"
      max_items: 100
      
  returns:
    success_response:
      success: true
      deleted_count: "int"
      deleted_ids: "list[int]"
      message: "str — Summary with missing IDs if applicable"
      
    error_response:
      error: "str — e.g., '❌ Maximum 100 tasks allowed'"
      
  behavior:
    - "Parse comma-separated string to list of ints"
    - "Validate max 100 items"
    - "DELETE WHERE id = ANY($1::int[]) AND user_id = $2"
    - "Report deleted IDs and missing IDs separately"
    
  example:
    request: |
      {"name": "batch_delete_tasks", "arguments": {"task_ids": "1,2,3"}}
      
    response: |
      {
        "success": true,
        "deleted_count": 3,
        "deleted_ids": [1, 2, 3],
        "message": "✅ Successfully deleted 3 task(s): #1, #2, #3"
      }
@end
```

```slc
@block CONTRACT tool_batch_update
priority: critical
intent: "batch_update_tasks API contract"
scope: global

content:
  name: "batch_update_tasks"
  category: "batch_operations"
  module: "batch_tools.py"
  
  signature: |
    async def batch_update_tasks(
        context: dict,
        task_ids: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> dict
    
  parameters:
    task_ids:
      type: "str"
      required: true
      format: "comma-separated integers"
      max_items: 100
      
    title:
      type: "Optional[str]"
      
    status:
      type: "Optional[str]"
      allowed_values: ["pending", "completed"]
      
    description:
      type: "Optional[str]"
      
    due_date:
      type: "Optional[str]"
      special_values: ["none" → NULL]
      
  returns:
    success_response:
      success: true
      updated_count: "int"
      updated_ids: "list[int]"
      message: "str — Summary of changes"
      
  behavior:
    - "Similar to update_task but for multiple IDs"
    - "Apply same value to all specified tasks"
    - "At least one value field required"
    - "Max 100 tasks"
@end
```

---

### SQL Operation Tools (2)

```slc
@block CONTRACT tool_generate_sql
priority: medium
intent: "generate_sql_query API contract"
scope: global

content:
  name: "generate_sql_query"
  category: "sql_operations"
  module: "sql_tools.py"
  
  signature: |
    async def generate_sql_query(
        context: dict,
        question: str
    ) -> dict
    
  parameters:
    question:
      type: "str"
      required: true
      description: "Natural language question"
      
  returns:
    success_response:
      success: true
      query: "str — Generated SQL query"
      message: "str — Formatted query with usage hint"
      
    no_match_response:
      success: true
      message: "str — Explanation of failure + schema hint"
      
  behavior:
    - "Use regex pattern matching for common queries"
    - "Include user_id filter in generated SQL"
    - "Do NOT execute query (only generate)"
    - "Suggest using execute_sql_query to run it"
@end
```

```slc
@block CONTRACT tool_execute_sql
priority: critical
intent: "execute_sql_query API contract"
scope: global

content:
  name: "execute_sql_query"
  category: "sql_operations"
  module: "sql_tools.py"
  
  signature: |
    async def execute_sql_query(
        context: dict,
        query: str
    ) -> dict
    
  parameters:
    query:
      type: "str"
      required: true
      constraints: "Must be SELECT query with user_id filter"
      
  returns:
    success_response:
      success: true
      row_count: "int"
      results: "str — Formatted table"
      
    error_response:
      error: "str — Validation or execution error"
      
  security_validation:
    - "Query must start with SELECT (case-insensitive)"
    - "Query must NOT contain DDL keywords: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, GRANT, REVOKE"
    - "Query must include 'user_id' filter"
    - "Execute with 30-second timeout"
    - "Limit display to 50 rows (show count if more)"
    
  behavior:
    - "Validate query before execution"
    - "Execute SELECT query"
    - "Format results as ASCII table"
    - "Sanitize error messages"
    
  example:
    request: |
      {
        "name": "execute_sql_query",
        "arguments": {
          "query": "SELECT id, title FROM todos WHERE user_id = 1"
        }
      }
      
    response: |
      {
        "success": true,
        "row_count": 3,
        "results": "id | title\n---+-------\n1  | Task 1\n..."
      }
@end
```

---

## MCP PROTOCOL CONTRACT

```slc
@block CONTRACT mcp_protocol
priority: critical
intent: "MCP protocol compliance requirements"
scope: global

content:
  protocol_version: "JSON-RPC 2.0"
  transport: "stdio"
  
  request_format:
    jsonrpc: '"2.0"'
    method: '"tools/call" or "tools/list"'
    params:
      name: "str — Tool name"
      arguments: "dict — Tool-specific arguments"
      _meta:
        userId: "int — User ID from main agent"
        
  response_format:
    jsonrpc: '"2.0"'
    id: "request.id"
    result:
      content:
        - type: "text"
          text: "JSON string of tool result"
          
  error_format:
    jsonrpc: '"2.0"'
    id: "request.id"
    error:
      code: "int — Error code"
      message: "str — Error message"
      
  tool_registration:
    method: "tools/list"
    returns:
      tools:
        - name: "str"
          description: "str"
          inputSchema:
            type: "object"
            properties: "dict"
            required: "list[str]"
@end
```

---

## ERROR CONTRACTS

```slc
@block CONTRACT error_responses
priority: high
intent: "Standardized error response formats"
scope: global

content:
  error_categories:
    validation_error:
      format: '{"error": "❌ Validation error message"}'
      examples:
        - "❌ Invalid status. Use 'pending' or 'completed'"
        - "❌ Invalid task IDs format. Use '1,2,3'"
        - "❌ Invalid due date format"
        
    not_found_error:
      format: '{"error": "❌ Resource not found message"}'
      examples:
        - "❌ Task #42 not found"
        - "❌ No tasks found with IDs: 1,2,3"
        
    security_error:
      format: '{"error": "❌ Security/permission error"}'
      examples:
        - "❌ Only SELECT queries are allowed"
        - "❌ Query must filter by user_id for security"
        - "❌ Modification queries are not allowed"
        
    database_error:
      format: '{"error": "❌ Generic database error"}'
      examples:
        - "❌ SQL Error: Please check your query syntax."
        - "❌ Database query failed"
        
  no_internal_details:
    rule: "Never expose stack traces, table names, or query internals"
@end
```

---

*End of CONTRACT.md — Read tasks/task_index.md next*

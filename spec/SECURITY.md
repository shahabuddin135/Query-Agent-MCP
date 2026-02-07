# SECURITY.md — Global Security Law

> **Authority: Level 2 (Only SPEC.md is higher)**
> Security rules OVERRIDE convenience, speed, and creativity.
> Violations are NEVER acceptable.

---

```slc
@block SECURITY core_principles
priority: critical
intent: "Fundamental security principles for this system"
scope: global
depends_on: none

content:
  principles:
    - "Defense in depth — multiple layers of protection"
    - "Principle of least privilege — minimal access required"
    - "Fail secure — errors must not expose data"
    - "Input validation — never trust user input"
    - "Output encoding — prevent injection attacks"
    
  security_by_default:
    - "All queries filter by user_id"
    - "All inputs validated before use"
    - "All errors sanitized before return"
    - "All credentials in environment variables"
@end
```

---

## DATABASE SECURITY

```slc
@block SECURITY database_rules
priority: critical
intent: "Database security enforcement rules"
scope: global

content:
  user_isolation:
    rule: "ALL database queries MUST filter by user_id"
    enforcement: "Runtime validation required"
    violation: "ABORT execution"
    
    examples:
      correct: |
        await conn.fetch(
            "SELECT * FROM todos WHERE user_id = $1",
            user_id
        )
        
      incorrect: |
        await conn.fetch("SELECT * FROM todos")
        # ❌ Missing user_id filter — FORBIDDEN
        
  sql_injection_prevention:
    rule: "Use parameterized queries ONLY"
    enforcement: "Code review and testing"
    violation: "Critical security flaw"
    
    examples:
      correct: |
        await conn.fetch(
            "SELECT * FROM todos WHERE id = $1 AND user_id = $2",
            task_id, user_id
        )
        
      incorrect: |
        query = f"SELECT * FROM todos WHERE id = {task_id}"
        # ❌ SQL injection risk — FORBIDDEN
        
  ddl_restrictions:
    rule: "No DDL operations allowed (CREATE/ALTER/DROP/TRUNCATE)"
    enforcement: "execute_sql_query validates query type"
    allowed: "SELECT only in execute_sql_query"
    
  connection_security:
    - "Use SSL/TLS for database connections (sslmode=require)"
    - "Connection string in environment variable only"
    - "Never log connection strings or credentials"
    - "Use connection pooling (min=1, max=10)"
@end
```

---

## INPUT VALIDATION

```slc
@block SECURITY input_validation
priority: critical
intent: "All inputs must be validated before use"
scope: global

content:
  validation_rules:
    task_id:
      type: "integer"
      validation: "Must be positive integer"
      example: "1, 42, 999"
      
    title:
      type: "string"
      validation: "1-255 characters, non-empty"
      sanitization: "Trim whitespace"
      
    description:
      type: "string"
      validation: "0-1000 characters"
      sanitization: "Trim whitespace, allow NULL"
      
    status:
      type: "enum"
      allowed_values: ["pending", "completed"]
      validation: "Must be exactly 'pending' or 'completed'"
      
    due_date:
      type: "ISO 8601 string or 'none'"
      validation: "Valid datetime or literal 'none'"
      parsing: "datetime.fromisoformat()"
      
    task_ids:
      type: "comma-separated integers"
      validation: "1-100 IDs, each positive integer"
      example: "1,2,3,42,100"
      
    keyword:
      type: "string"
      validation: "Non-empty string"
      sanitization: "Escape SQL wildcards for ILIKE"
      
    query:
      type: "SQL string"
      validation: "Must start with SELECT, no DDL keywords"
      enforcement: "Regex + keyword blacklist"
@end
```

---

## OUTPUT SANITIZATION

```slc
@block SECURITY output_sanitization
priority: high
intent: "Prevent information leakage in responses"
scope: global

content:
  error_messages:
    rule: "Never expose internal details in errors"
    
    examples:
      correct: |
        {"error": "❌ Task not found"}
        
      incorrect: |
        {"error": "SELECT failed: relation todos does not exist at line 42"}
        # ❌ Exposes database internals
        
  credential_handling:
    - "Never return database connection strings"
    - "Never log passwords or tokens"
    - "Never include user_id in error messages to other users"
    
  data_filtering:
    - "Always verify user_id matches returned data"
    - "Never return other users' tasks"
    - "Limit result sets to prevent DoS (max 1000 rows)"
@end
```

---

## AUTHENTICATION & AUTHORIZATION

```slc
@block SECURITY auth_rules
priority: critical
intent: "User context handling and authorization"
scope: global

content:
  user_context:
    source: "Passed from main agent via MCP _meta.userId"
    validation: "Must be positive integer"
    default: "FORBIDDEN — must be explicit"
    
  authorization_model:
    rule: "Users can only access their own data"
    enforcement: "user_id filter in ALL queries"
    
    examples:
      - "User A cannot see User B's tasks"
      - "User A cannot modify User B's tasks"
      - "User A cannot execute queries on User B's behalf"
      
  api_key_authentication:
    rationale: |
      The MCP server is exposed over Streamable HTTP transport.
      All incoming requests MUST include a valid API key.
      This prevents unauthorized access to the HTTP endpoint.
      
    implementation:
      method: "Starlette middleware wrapping the ASGI app"
      header: "Authorization: Bearer <MCP_API_KEY>"
      env_var: "MCP_API_KEY"
      behavior:
        missing_key: "Return 401 Unauthorized with JSON error"
        invalid_key: "Return 401 Unauthorized with JSON error"
        valid_key: "Pass request through to MCP handler"
      excluded_paths:
        - "/health" # Health check endpoint (if added)
        
    rules:
      - "MCP_API_KEY MUST be set in environment variables"
      - "Server MUST refuse to start if MCP_API_KEY is not set"
      - "API key MUST be compared using constant-time comparison (hmac.compare_digest)"
      - "Failed auth attempts MUST be logged with client IP"
      - "API key MUST NOT appear in logs or error responses"
      
  user_context:
    source: "Passed from main agent via MCP _meta.userId"
    validation: "Must be positive integer"
    default: "FORBIDDEN — must be explicit"
    
    note: |
      API key authenticates the CLIENT (agent system).
      user_id authorizes DATA ACCESS (row-level security).
      Both layers are required for full security.
@end
```

---

## BATCH OPERATION SECURITY

```slc
@block SECURITY batch_limits
priority: critical
intent: "Prevent abuse via batch operations"
scope: global

content:
  max_batch_size: 100
  
  enforcement:
    rule: "Reject batch operations with > 100 items"
    error: "❌ Maximum 100 tasks allowed"
    
  rationale: |
    - Prevent DoS via large batch deletes/updates
    - Keep transaction size manageable
    - Limit lock duration on database
    
  validation:
    - "Parse comma-separated IDs"
    - "Count items before execution"
    - "Reject if count > 100"
    - "Return error immediately (do not attempt partial execution)"
@end
```

---

## SQL QUERY EXECUTION SECURITY

```slc
@block SECURITY sql_execution
priority: critical
intent: "execute_sql_query and generate_sql_query security rules"
scope: global

content:
  allowed_operations:
    - "SELECT queries only"
    
  forbidden_operations:
    - "INSERT, UPDATE, DELETE"
    - "CREATE, ALTER, DROP"
    - "TRUNCATE, GRANT, REVOKE"
    - "EXEC, EXECUTE, CALL (stored procedures)"
    - "INTO (SELECT INTO / INSERT INTO)"
    
  table_restrictions:
    rule: "Only the 'todos' table may be queried"
    enforcement: "Table allowlist validation before execution"
    allowed_tables:
      - "todos"
    blocked_tables:
      - "users (contains hashed_password — NEVER expose)"
      - "conversation_messages"
      - "Any other table"
    rationale: |
      The 'users' table contains hashed_password and email fields.
      Allowing arbitrary table queries could leak sensitive data.
      The table allowlist is enforced by regex extraction of FROM/JOIN targets.
      
  injection_prevention:
    semicolons: "BLOCKED — prevents query chaining / stacked queries"
    comments: "BLOCKED — SQL comments (-- and /* */) stripped or rejected"
    parameterized_user_id: |
      execute_sql_query enforces parameterized user_id via regex substitution.
      Literal user_id values (WHERE user_id = 123) are replaced with $1 placeholder.
      The actual user_id is passed as a query parameter at execution time.
      
  generate_sql_query_rules:
    rule: "All generated queries MUST use parameterized placeholders ($1, $2)"
    enforcement: "generate_sql_query returns query + params array"
    examples:
      correct: |
        query = "SELECT * FROM todos WHERE user_id = $1"
        params = [user_id]
      incorrect: |
        query = f"SELECT * FROM todos WHERE user_id = {user_id}"
        # ❌ f-string interpolation — SQL injection risk — FORBIDDEN
    
  validation_sequence:
    1. "Normalize query: strip whitespace, uppercase for keyword check"
    2. "Check query starts with SELECT (case-insensitive)"
    3. "Check for forbidden keywords (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, GRANT, REVOKE, INTO, EXEC, EXECUTE)"
    4. "Block semicolons (prevents query chaining)"
    5. "Block SQL comments (-- and /* */)"
    6. "Validate tables against allowlist (only 'todos' allowed)"
    7. "Enforce parameterized user_id ($1 placeholder)"
    8. "Execute with timeout (30 seconds)"
    9. "Limit results to 50 rows in display"
    
  keyword_blacklist:
    - "DROP"
    - "DELETE"
    - "UPDATE"
    - "INSERT"
    - "ALTER"
    - "TRUNCATE"
    - "GRANT"
    - "REVOKE"
    - "INTO"
    - "EXEC"
    - "EXECUTE"
    
  vulnerability_history:
    - id: "VULN-001"
      severity: "CRITICAL"
      found: "Security audit"
      description: "generate_sql_query used f-string interpolation for user_id and keyword"
      example: 'f"...WHERE user_id = {user_id}" and f"...ILIKE \'%{keyword}%\'"'
      fix: "Replaced with parameterized queries ($1, $2) and params array"
      status: "FIXED"
      
    - id: "VULN-002"
      severity: "HIGH"
      found: "Security audit"
      description: "execute_sql_query had no table restrictions — could query 'users' table"
      fix: "Added table allowlist (only 'todos'), blocked semicolons/comments, added INTO/EXEC/EXECUTE to blacklist"
      status: "FIXED"
      
  examples:
    allowed: |
      SELECT id, title FROM todos WHERE user_id = $1
      
    forbidden: |
      DELETE FROM todos WHERE user_id = 1
      # ❌ Modification not allowed
      
      SELECT * FROM users WHERE id = 1
      # ❌ 'users' table not in allowlist
      
      SELECT * FROM todos WHERE user_id = 1; DROP TABLE todos;
      # ❌ Semicolons blocked — query chaining forbidden
@end
```

---

## ENVIRONMENT SECURITY

```slc
@block SECURITY environment_vars
priority: critical
intent: "Secure handling of environment variables"
scope: global

content:
  secrets_in_env:
    - "DATABASE_URL must be in .env (not in code)"
    - "MCP_API_KEY must be in .env (not in code)"
    - "Never commit .env to version control"
    - "Use .env.example for template only (placeholder values)"
    
  required_secrets:
    DATABASE_URL:
      purpose: "PostgreSQL connection string"
      format: "postgresql://user:pass@host/db?sslmode=require"
      required: true
      
    MCP_API_KEY:
      purpose: "API key for authenticating HTTP requests"
      format: "Minimum 32 character random string"
      required: true
      generation: "Use secrets.token_urlsafe(32) or similar"
      
  logging_rules:
    - "Never log DATABASE_URL value"
    - "Never log MCP_API_KEY value"
    - "Never log user passwords or tokens"
    - "Log only sanitized query parameters"
    - "Log failed auth attempts (without revealing the submitted key)"
    
  .gitignore_required:
    - ".env"
    - ".venv/"
    - "**/__pycache__/"
    - "*.pyc"
@end
```

---

## ERROR HANDLING SECURITY

```slc
@block SECURITY error_handling
priority: high
intent: "Secure error handling and logging"
scope: global

content:
  error_responses:
    rule: "Return structured errors without internal details"
    
    format: |
      {
        "error": "User-friendly message",
        "code": "ERROR_CODE" (optional)
      }
      
  no_stack_traces:
    rule: "Never return stack traces to MCP client"
    enforcement: "Catch all exceptions, sanitize before return"
    
  no_internal_details:
    rule: "Never include database error strings in client responses"
    enforcement: "All except blocks use generic messages"
    
    examples:
      correct: |
        except Exception as e:
            logger.error(f"Database error creating task: {e}")
            return {"error": "❌ Database error while creating task"}
            
      incorrect: |
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}
            # ❌ Exposes PostgreSQL error message to client — FORBIDDEN
    
  vulnerability_history:
    - id: "VULN-003"
      severity: "MEDIUM"
      found: "Security audit"
      description: "All tool files used f'Database error: {str(e)}' exposing PostgreSQL internals"
      affected_files:
        - "task_tools.py"
        - "batch_tools.py"
        - "sql_tools.py"
        - "server.py"
      fix: "Replaced with generic messages + logger.error() in all files"
      status: "FIXED"
    
  logging_strategy:
    - "Log full errors internally via logger.error() (for debugging)"
    - "Return generic sanitized errors to client"
    - "Include context (operation name) in log messages"
    - "Use Python logging module (import logging) — not print()"
    
  examples:
    correct: |
      try:
          result = await conn.fetch(query)
      except Exception as e:
          # Log full error
          logger.error(f"Query failed: {e}")
          # Return sanitized error
          return {"error": "❌ Database query failed"}
          
    incorrect: |
      try:
          result = await conn.fetch(query)
      except Exception as e:
          return {"error": str(e)}
          # ❌ Exposes internal error details
@end
```

---

## CONNECTION POOL SECURITY

```slc
@block SECURITY connection_pool
priority: high
intent: "Secure database connection pool management"
scope: global

content:
  pool_configuration:
    min_size: 1
    max_size: 10
    timeout: 30
    ssl_mode: "require"
    
  connection_lifecycle:
    - "Create pool on server start"
    - "Reuse connections (do not create per request)"
    - "Close pool on server shutdown"
    - "Never store credentials in memory beyond pool initialization"
    
  error_handling:
    - "Handle connection failures gracefully"
    - "Retry logic for transient failures"
    - "Do not expose connection errors to client"
@end
```

---

## SECURITY TESTING REQUIREMENTS

```slc
@block SECURITY testing
priority: high
intent: "Security validation and testing requirements"
scope: global

content:
  required_tests:
    - "SQL injection attempts (should fail)"
    - "User isolation (User A cannot access User B data)"
    - "Batch size limits (> 100 items should fail)"
    - "DDL queries in execute_sql_query (should fail)"
    - "Missing user_id in queries (should fail)"
    - "Table allowlist bypass (querying 'users' table should fail)"
    - "Semicolon injection (query chaining should fail)"
    - "SQL comment injection (-- and /* */ should fail)"
    - "API key authentication (missing/invalid key returns 401)"
    - "Error message leaking (no PostgreSQL internals in responses)"
    
  test_cases:
    sql_injection:
      - "task_id = '1; DROP TABLE todos;'"
      - "keyword = '\'; DELETE FROM todos--'"
      - "user_id = '1 OR 1=1'"
      
    user_isolation:
      - "User 1 tries to access User 2's task"
      - "User 1 tries to delete User 2's task"
      
    batch_limits:
      - "Submit 101 task IDs in batch_delete"
      - "Submit 150 task IDs in batch_update"
      
    table_restrictions:
      - "SELECT * FROM users WHERE id = 1 → REJECTED"
      - "SELECT * FROM conversation_messages → REJECTED"
      - "SELECT * FROM todos JOIN users ON ... → REJECTED"
      
    injection_prevention:
      - "SELECT * FROM todos; DROP TABLE todos → REJECTED (semicolon)"
      - "SELECT * FROM todos -- WHERE user_id = 1 → REJECTED (comment)"
      - "SELECT * FROM todos /* bypass */ → REJECTED (block comment)"
      
    api_key_auth:
      - "Request without Authorization header → 401"
      - "Request with invalid Bearer token → 401"
      - "Request with valid Bearer token → passes through"
      - "Request with empty MCP_API_KEY env → server refuses to start"
      
    error_sanitization:
      - "Trigger DB error → response must NOT contain PostgreSQL error text"
      - "Trigger connection error → response must say 'Database error' generically"
@end
```

---

## SECURITY VIOLATION HANDLING

```slc
@block SECURITY violation_response
priority: critical
intent: "How to respond when security rules are violated"
scope: global

content:
  response_protocol:
    1. "STOP execution immediately"
    2. "Log security violation with details"
    3. "Return generic error to client (no details)"
    4. "Alert operator if critical"
    
  examples:
    missing_user_id:
      action: "ABORT query"
      log: "SECURITY: Query missing user_id filter"
      return: '{"error": "❌ Invalid query"}'
      
    sql_injection_attempt:
      action: "REJECT query"
      log: "SECURITY: Potential SQL injection in query"
      return: '{"error": "❌ Invalid input"}'
      
    unauthorized_access:
      action: "DENY operation"
      log: "SECURITY: User attempted to access other user data"
      return: '{"error": "❌ Access denied"}'
@end
```

---

*End of SECURITY.md — Read MEMORY.md next*

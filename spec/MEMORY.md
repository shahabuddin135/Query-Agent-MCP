# MEMORY.md — Anti-Hallucination Anchor

> **Authority: Level 3**
> Frozen facts and decisions that prevent drift and hallucination.
> In case of conflict, MEMORY.md wins over implementation details.

---

```slc
@block MEMORY project_decisions
priority: critical
intent: "Immutable project decisions"
scope: global
depends_on: [CONTEXT.project_goal, CONSTRAINTS.tech_stack]

content:
  created: "2026-02-07"
  last_updated: "2026-02-07"
  status: "active"
  
  decision_log: |
    This file tracks all frozen decisions to prevent drift.
    Append-only. Do not modify existing entries.
@end
```

---

## FROZEN DECISIONS

```slc
@block MEMORY decision_001_python_over_typescript
priority: critical
intent: "Why Python instead of TypeScript"
scope: global

content:
  decision_id: "D001"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "Use Python for MCP server, not TypeScript"
  
  rationale:
    - "Main agent is already Python (FastAPI + SQLModel)"
    - "Reuse existing asyncpg experience"
    - "Team familiarity with Python async patterns"
    - "Easier integration with existing codebase"
    
  alternatives_considered:
    - "TypeScript + @modelcontextprotocol/sdk"
      rejected_because: "Different runtime, harder integration"
      
  immutable: true
  cannot_change_without: "Full project restart"
@end
```

```slc
@block MEMORY decision_002_asyncpg_over_sqlmodel
priority: critical
intent: "Why asyncpg instead of SQLModel ORM"
scope: global

content:
  decision_id: "D002"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "Use asyncpg with direct SQL, not SQLModel ORM"
  
  rationale:
    - "Lightweight — no ORM overhead"
    - "Direct control over SQL queries"
    - "Better performance for simple CRUD"
    - "Easier debugging (see exact SQL)"
    - "Schema already exists (no migrations needed)"
    
  alternatives_considered:
    - "SQLModel ORM"
      rejected_because: "Overkill for simple CRUD, adds complexity"
    - "psycopg2"
      rejected_because: "Not async, poor performance"
      
  immutable: true
@end
```

```slc
@block MEMORY decision_003_stdio_transport
priority: critical
intent: "Why stdio transport instead of HTTP"
scope: global

content:
  decision_id: "D003"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "Use stdio transport for MCP communication"
  
  rationale:
    - "Standard MCP pattern"
    - "Simpler than HTTP server"
    - "No port conflicts"
    - "Process-level isolation"
    - "Easy integration with main agent"
    
  alternatives_considered:
    - "HTTP transport"
      rejected_because: "Unnecessary complexity, port management"
    - "WebSocket transport"
      rejected_because: "Not needed for single agent use case"
      
  immutable: true
@end
```

```slc
@block MEMORY decision_004_individual_task_files
priority: high
intent: "Why individual task files instead of monolithic TASKS.md"
scope: global

content:
  decision_id: "D004"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "Use individual task files (phases/phase-N/X.X_task.md)"
  
  rationale:
    - "Context efficiency — load only needed task (~2KB vs 64KB)"
    - "97% reduction in context window usage"
    - "Clean git history per task"
    - "Easy status updates without large file diffs"
    - "Better parallelization potential"
    
  structure: |
    tasks/
    ├── task_index.md (HOT: 8KB registry)
    └── phases/
        ├── phase-1/
        │   ├── 1.1_init_project.md
        │   ├── 1.2_structure.md
        │   └── ...
        ├── phase-2/
        └── phase-3/
        
  immutable: true
@end
```

```slc
@block MEMORY decision_005_created_by_format
priority: medium
intent: "Format for created_by field in todos"
scope: global

content:
  decision_id: "D005"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "Use format 'task created by \\'username\\'' for created_by field"
  
  format: "task created by 'username'"
  example: "task created by 'john_doe'"
  
  implementation: |
    # Fetch username from users table
    user = await conn.fetchrow("SELECT username FROM users WHERE id = $1", user_id)
    username = user['username'] if user else 'unknown'
    created_by = f"task created by '{username}'"
    
  rationale:
    - "Human-readable audit trail"
    - "Consistent format across all tasks"
    - "Easy to parse if needed"
    
  immutable: true
@end
```

```slc
@block MEMORY decision_006_oldest_first_listing
priority: medium
intent: "Why list tasks oldest-to-newest instead of newest-first"
scope: global

content:
  decision_id: "D006"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "List tasks in ascending order by created_at (oldest first)"
  
  query: "ORDER BY created_at ASC"
  
  rationale:
    - "Oldest tasks likely need attention first"
    - "FIFO queue behavior"
    - "Matches user's mental model for task lists"
    
  alternatives_considered:
    - "Newest first (DESC)"
      rejected_because: "Recent tasks less urgent than old ones"
      
  immutable: true
@end
```

---

## ASSUMPTIONS

```slc
@block MEMORY assumptions
priority: high
intent: "Explicit assumptions that must hold true"
scope: global

content:
  database_assumptions:
    - "Neon PostgreSQL schema exists and is stable"
    - "users table has id and username columns"
    - "todos table has all required columns"
    - "user_id foreign key relationship exists"
    
  integration_assumptions:
    - "Main agent passes user_id via MCP _meta.userId"
    - "Main agent handles authentication"
    - "Main agent manages user sessions"
    
  environment_assumptions:
    - "DATABASE_URL is always set in environment"
    - "Python 3.11+ runtime available"
    - "Network access to Neon PostgreSQL"
    
  if_assumption_violated:
    action: "ABORT and report which assumption failed"
@end
```

---

## DO NOT CHANGE

```slc
@block MEMORY immutable_facts
priority: critical
intent: "Facts that CANNOT be changed"
scope: global

content:
  immutable_facts:
    - "Project name: query-agent-mcp"
    - "Language: Python 3.11+"
    - "Database: Neon PostgreSQL"
    - "Transport: stdio only"
    - "Tool count: 10 (6 + 2 + 2)"
    - "Batch limit: 100 items max"
    - "Status values: 'pending' or 'completed' only"
    - "User isolation: ALL queries filter by user_id"
    
  immutable_structure:
    - "src/mcp_server/ package structure"
    - "tools/ subdirectory for tool modules"
    - "spec/ directory for SLC files"
    
  immutable_contracts:
    - "Tool names must match MCP registration exactly"
    - "Tool responses must be TextContent type"
    - "All tool functions are async"
    - "All tool functions receive context dict"
@end
```

---

## TOOL SPECIFICATIONS (FROZEN)

```slc
@block MEMORY tool_specs
priority: critical
intent: "Exact tool definitions — cannot be changed"
scope: global

content:
  tool_count: 10
  
  task_management_tools: 6
    - create_task
    - list_tasks
    - update_task
    - delete_task
    - get_task_details
    - search_tasks_by_keyword
    
  batch_operation_tools: 2
    - batch_delete_tasks
    - batch_update_tasks
    
  sql_operation_tools: 2
    - generate_sql_query
    - execute_sql_query
    
  no_additional_tools: "Do not add tools beyond these 10"
  no_tool_removal: "Do not remove any of these 10 tools"
  
  immutable: true
@end
```

---

## CHANGE LOG (APPEND-ONLY)

```slc
@block MEMORY change_log
priority: high
intent: "Track all changes to specs (append-only)"
scope: global

content:
  format: "YYYY-MM-DD | Change description | Reason | Updated files"
  
  changes:
    - date: "2026-02-07"
      change: "Initial spec creation"
      reason: "Bootstrap project with SLC structure"
      files: "All spec/ files created"
      approved_by: "user"
@end
```

---

## KNOWN LIMITATIONS

```slc
@block MEMORY limitations
priority: medium
intent: "Known limitations accepted as design tradeoffs"
scope: global

content:
  accepted_limitations:
    - "No authentication layer (relies on main agent)"
    - "No rate limiting (agent layer responsibility)"
    - "No caching layer (direct DB queries)"
    - "No transaction rollback for batch ops (all-or-nothing not supported)"
    - "No streaming results (load all in memory)"
    - "No pagination (return all matching rows)"
    
  rationale: |
    These limitations are ACCEPTABLE because:
    - This is an internal tool for trusted agent
    - Scale is small (1-10 concurrent requests)
    - Simplicity > feature richness
    - Main agent handles auth/rate limiting
    
  not_limitations: |
    These are NOT limitations (they're features):
    - User isolation enforcement
    - SQL injection prevention
    - Batch size limits
@end
```

---

## CONFLICT RESOLUTION

```slc
@block MEMORY conflict_resolution
priority: critical
intent: "How to resolve conflicts with MEMORY.md"
scope: global

content:
  if_code_conflicts_with_memory:
    rule: "MEMORY.md wins"
    action: "Update code to match MEMORY.md"
    exception: "User explicitly overrides and updates MEMORY.md"
    
  if_spec_conflicts_with_memory:
    rule: "MEMORY.md wins"
    action: "Update spec to match MEMORY.md"
    exception: "User explicitly approves spec change and updates MEMORY.md"
    
  if_implementation_differs:
    rule: "Flag as drift"
    action: "Report difference and ask user to resolve"
    
  updating_memory:
    rule: "Append-only (do not delete or modify existing entries)"
    format: "Add new entry to CHANGE LOG"
    approval: "User must approve all MEMORY.md changes"
@end
```

```slc
@block MEMORY decision_007_individual_task_files
priority: critical
intent: "Corrected structure violation - individual task files"
scope: global

content:
  decision_id: "D007"
  date: "2026-02-07"
  status: "frozen"
  
  decision: "Use individual task files in phases/ directories, not monolithic task_index.md"
  
  violation_detected:
    - "Phase 1 executed without individual task files"
    - "task_index.md was 444 lines (should be <150)"
    - "Empty phases/phase-N/ directories"
    
  correction_applied:
    - "Created 26 individual task files"
    - "Phase 1: 8 files in phases/phase-1/"
    - "Phase 2: 14 files in phases/phase-2/"
    - "Phase 3: 4 files in phases/phase-3/"
    - "Reduced task_index.md to 225 lines (4.62 KB)"
    
  rationale:
    - "Follows SLC_UNIVERSAL_STRUCTURE.md Section 8"
    - "Achieves 97% context window reduction per task"
    - "Individual files ~2KB each"
    - "task_index.md now router-only"
    
  lesson_learned:
    - "Validate structure BEFORE execution, not after"
    - "Pre-execution validation saves time and tokens"
    - "Would have caught this before Phase 1 started"
    
  immutable: true
@end
```

---

## VERIFICATION CHECKLIST

```slc
@block MEMORY verification
priority: high
intent: "Checklist to verify implementation matches MEMORY.md"
scope: global

content:
  before_execution:
    - "Verify Python 3.11+ used"
    - "Verify asyncpg used (not SQLModel)"
    - "Verify stdio transport (not HTTP)"
    - "Verify 10 tools defined"
    - "Verify all queries filter by user_id"
    - "Verify created_by format matches"
    - "Verify list_tasks uses ORDER BY created_at ASC"
    
  during_execution:
    - "Verify task status updates in task_index.md"
    - "Verify no code outside spec/"
    - "Verify no dependencies beyond CONSTRAINTS.md"
    
  after_completion:
    - "Verify all 10 tools implemented"
    - "Verify all security rules enforced"
    - "Verify no MEMORY.md violations"
@end
```

---

*End of MEMORY.md — Read backend_specs/ARCH.md next*

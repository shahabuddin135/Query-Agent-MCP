# PLAN.md — Execution Plan

> **Authority: Level 7**
> Defines high-level execution phases and milestones.
> No implementation details. No code.

---

```slc
@block PLAN project_phases
priority: critical
intent: "Overall project execution strategy"
scope: global
depends_on: [ARCH.system_overview, CONSTRAINTS.tech_stack]

content:
  total_phases: 3
  total_tasks: 26
  estimated_time: 180
  
  execution_model: "Sequential phases with individual task files"
  
  phase_dependencies:
    - "Phase 1 must complete before Phase 2"
    - "Phase 2 must complete before Phase 3"
    - "No parallel phase execution"
@end
```

---

## PHASE OVERVIEW

```slc
@block PLAN phase_summary
priority: critical
intent: "High-level phase breakdown"
scope: global

content:
  phases:
    phase_1:
      name: "Foundation & Infrastructure"
      tasks: 8
      estimate: 60
      deliverables:
        - "Project structure created"
        - "Database layer implemented"
        - "MCP server skeleton ready"
        - "Environment configuration"
        
    phase_2:
      name: "Tool Implementation"
      tasks: 14
      estimate: 90
      deliverables:
        - "All 10 tools implemented"
        - "Security rules enforced"
        - "Error handling in place"
        
    phase_3:
      name: "Integration & Testing"
      tasks: 4
      estimate: 30
      deliverables:
        - "All tools tested"
        - "Integration validated"
        - "Documentation complete"
        - "Ready for deployment"
@end
```

---

## PHASE 1: Foundation & Infrastructure

```slc
@block PLAN phase_1
priority: critical
intent: "Foundation setup and infrastructure"
scope: phase-1
depends_on: none

content:
  name: "Foundation & Infrastructure"
  goal: "Set up project structure, database layer, and MCP server skeleton"
  
  tasks: 8
  estimate: 60
  
  task_overview:
    - "1.1 Initialize project with UV/pip"
    - "1.2 Create directory structure"
    - "1.3 Configure environment variables"
    - "1.4 Implement database.py"
    - "1.5 Create tool module stubs"
    - "1.6 Implement MCP server skeleton"
    - "1.7 Test database connection"
    - "1.8 Test MCP server startup"
    
  acceptance_criteria:
    - "pyproject.toml exists with correct dependencies"
    - "src/mcp_server/ structure created"
    - ".env configured with DATABASE_URL"
    - "Database pool connects successfully"
    - "MCP server starts and responds to tools/list"
    
  dependencies:
    - "Neon PostgreSQL database accessible"
    - "Python 3.11+ installed"
    - "UV or pip available"
@end
```

---

## PHASE 2: Tool Implementation

```slc
@block PLAN phase_2
priority: critical
intent: "Implement all 10 MCP tools"
scope: phase-2
depends_on: [PLAN.phase_1]

content:
  name: "Tool Implementation"
  goal: "Implement all 10 tools with security and error handling"
  
  tasks: 14
  estimate: 90
  
  task_groups:
    task_management_tools:
      tasks: 7
      estimate: 45
      tools:
        - "create_task (2.1)"
        - "list_tasks (2.2)"
        - "update_task (2.3)"
        - "delete_task (2.4)"
        - "get_task_details (2.5)"
        - "search_tasks_by_keyword (2.6)"
        - "Register task tools in server.py (2.7)"
        
    batch_operation_tools:
      tasks: 3
      estimate: 20
      tools:
        - "batch_delete_tasks (2.8)"
        - "batch_update_tasks (2.9)"
        - "Register batch tools in server.py (2.10)"
        
    sql_operation_tools:
      tasks: 4
      estimate: 25
      tools:
        - "generate_sql_query (2.11)"
        - "execute_sql_query (2.12)"
        - "Register SQL tools in server.py (2.13)"
        - "Validate all 10 tools registered (2.14)"
        
  acceptance_criteria:
    - "All 10 tools implemented in respective modules"
    - "All tools registered in server.py"
    - "All tools enforce user_id filtering"
    - "All tools use parameterized queries"
    - "All tools return structured dicts"
    - "created_by format matches spec"
    - "list_tasks sorts by created_at ASC"
    
  security_validation:
    - "Every query filters by user_id"
    - "No SQL injection vectors"
    - "Batch limits enforced (max 100)"
    - "execute_sql_query validates query type"
@end
```

---

## PHASE 3: Integration & Testing

```slc
@block PLAN phase_3
priority: critical
intent: "Test and validate complete system"
scope: phase-3
depends_on: [PLAN.phase_2]

content:
  name: "Integration & Testing"
  goal: "Validate all tools work correctly and meet security requirements"
  
  tasks: 4
  estimate: 30
  
  task_overview:
    - "3.1 Test all 10 tools via MCP protocol"
    - "3.2 Validate user isolation (security testing)"
    - "3.3 Create README.md and documentation"
    - "3.4 Final integration test with main agent"
    
  test_coverage:
    functional_tests:
      - "Create task with due_date"
      - "List tasks with status filter"
      - "Update task (all field combinations)"
      - "Delete task"
      - "Get task details"
      - "Search tasks by keyword"
      - "Batch delete (< 100 and > 100)"
      - "Batch update multiple fields"
      - "Generate SQL query from NL"
      - "Execute safe SELECT query"
      
    security_tests:
      - "SQL injection attempts (should fail)"
      - "User isolation (User A cannot access User B data)"
      - "Batch size over 100 (should fail)"
      - "DDL in execute_sql_query (should fail)"
      - "Missing user_id filter (should fail)"
      
    integration_tests:
      - "Main agent calls tools via stdio"
      - "User context passed correctly"
      - "Results returned as TextContent"
      
  acceptance_criteria:
    - "All functional tests pass"
    - "All security tests fail correctly"
    - "Integration with main agent works"
    - "Documentation complete"
    - "Ready for deployment"
@end
```

---

## MILESTONES

```slc
@block PLAN milestones
priority: high
intent: "Key project milestones and approval gates"
scope: global

content:
  milestones:
    M1_foundation_complete:
      phase: "Phase 1"
      criteria: "Database layer + MCP server skeleton working"
      approval_required: false
      
    M2_tools_implemented:
      phase: "Phase 2"
      criteria: "All 10 tools implemented and registered"
      approval_required: true
      note: "User must approve before Phase 3"
      
    M3_testing_complete:
      phase: "Phase 3"
      criteria: "All tests passing, security validated"
      approval_required: true
      note: "User must approve before deployment"
      
    M4_deployment_ready:
      phase: "Phase 3"
      criteria: "Documentation complete, integration validated"
      approval_required: true
      note: "Final approval before production deployment"
@end
```

---

## EXECUTION STRATEGY

```slc
@block PLAN execution_strategy
priority: high
intent: "How to execute tasks efficiently"
scope: global

content:
  task_execution_model:
    pattern: "Sequential execution via task_index.md router"
    
    process:
      1. "Read task_index.md (HOT: 8KB)"
      2. "Get current task ID and file path"
      3. "Load individual task file (WARM: ~2KB)"
      4. "Fetch Context7 docs if needed for libraries/services"
      5. "Execute task content"
      6. "Update task status in task_index.md"
      7. "Continue to next task"
      
  context_efficiency:
    hot_tier: "task_index.md — loaded once per session"
    warm_tier: "Individual task files — loaded per execution"
    total_per_task: "~10KB context (97% reduction vs monolithic)"
    
  validation_points:
    before_each_task:
      - "Verify dependencies satisfied"
      - "Verify Context7 docs fetched if needed"
      - "Verify spec compliance"
      
    after_each_task:
      - "Update task_index.md status"
      - "Verify acceptance criteria met"
      - "Run quick smoke test"
      
    after_each_phase:
      - "Run phase validation tests"
      - "Update MEMORY.md change log"
      - "Request user approval if milestone"
@end
```

---

## DEPENDENCY GRAPH

```slc
@block PLAN dependencies
priority: medium
intent: "Task dependency visualization"
scope: global

content:
  dependency_chain: |
    Phase 1 (Foundation)
    ├── 1.1 Initialize project
    ├── 1.2 Create structure (depends on 1.1)
    ├── 1.3 Configure .env (depends on 1.2)
    ├── 1.4 Implement database.py (depends on 1.3)
    ├── 1.5 Create tool stubs (depends on 1.2)
    ├── 1.6 Implement server.py (depends on 1.4, 1.5)
    ├── 1.7 Test DB connection (depends on 1.4)
    └── 1.8 Test MCP startup (depends on 1.6)
    
    Phase 2 (Tools)
    ├── Task Tools (2.1-2.6)
    │   └── 2.7 Register task tools (depends on 2.1-2.6)
    ├── Batch Tools (2.8-2.9)
    │   └── 2.10 Register batch tools (depends on 2.8-2.9)
    ├── SQL Tools (2.11-2.12)
    │   └── 2.13 Register SQL tools (depends on 2.11-2.12)
    └── 2.14 Validate all tools (depends on 2.7, 2.10, 2.13)
    
    Phase 3 (Testing)
    ├── 3.1 Test all tools (depends on Phase 2 complete)
    ├── 3.2 Security testing (depends on 3.1)
    ├── 3.3 Documentation (can parallel with 3.1-3.2)
    └── 3.4 Integration test (depends on 3.1, 3.2)
    
  critical_path:
    - "1.1 → 1.2 → 1.3 → 1.4 → 1.6 → Phase 2 → 3.1 → 3.2 → 3.4"
@end
```

---

## RISK MITIGATION

```slc
@block PLAN risks
priority: medium
intent: "Identified risks and mitigation strategies"
scope: global

content:
  risks:
    database_connection_issues:
      probability: "medium"
      impact: "high"
      mitigation:
        - "Test connection early (task 1.7)"
        - "Validate DATABASE_URL format"
        - "Check network connectivity to Neon"
        
    mcp_protocol_complexity:
      probability: "low"
      impact: "medium"
      mitigation:
        - "Use official MCP Python SDK"
        - "Fetch Context7 docs for MCP before implementation"
        - "Test tools/list early (task 1.8)"
        
    security_rule_violations:
      probability: "medium"
      impact: "critical"
      mitigation:
        - "Security testing in Phase 3"
        - "Code review for user_id filtering"
        - "Validate parameterized queries"
        
    batch_operation_edge_cases:
      probability: "medium"
      impact: "low"
      mitigation:
        - "Test with exactly 100 items"
        - "Test with 101 items (should fail)"
        - "Test with malformed ID lists"
@end
```

---

## QUALITY GATES

```slc
@block PLAN quality_gates
priority: high
intent: "Quality criteria that must be met"
scope: global

content:
  code_quality:
    - "All functions have docstrings"
    - "All queries use parameterized syntax"
    - "All tool functions are async"
    - "No print() statements (use logging)"
    
  security_quality:
    - "All queries filter by user_id"
    - "No SQL injection vectors"
    - "No credential logging"
    - "Batch limits enforced"
    
  functional_quality:
    - "All 10 tools registered"
    - "All tools return structured dicts"
    - "created_by format correct"
    - "list_tasks sorts correctly (ASC)"
    
  integration_quality:
    - "MCP protocol compliance"
    - "stdio transport works"
    - "Compatible with main agent"
@end
```

---

*End of PLAN.md — Read CONTRACT.md next*

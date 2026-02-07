# SPEC.md — Global Router (Entry Point)

> **Authority: HIGHEST**
> This file is the **mandatory entry point** for the query-agent-mcp project.
> LLMs MUST read this file first and follow the read order strictly.

---

```slc
@block INDEX root_router
priority: critical
intent: "Main entry point and execution router for query-agent-mcp"
scope: global
failure_if_skipped: true

content:
  project_name: "query-agent-mcp"
  version: "1.0.0"
  description: "Python MCP server for Neon task management with 10 tools"
@end
```

---

## READ ORDER (MANDATORY)

**LLMs must read files in this exact order. No deviation allowed.**

1. **CONTEXT.md** — Project intent and boundaries
2. **CONSTRAINTS.md** — Technical constraints and hard limits
3. **SECURITY.md** — Security rules (overrides all)
4. **MEMORY.md** — Frozen decisions and facts
5. **backend_specs/ARCH.md** — System architecture
6. **backend_specs/PLAN.md** — Execution phases
7. **backend_specs/CONTRACT.md** — API contracts and schemas
8. **backend_specs/tasks/task_index.md** — Global task registry (HOT)

---

## EXECUTION RULES

```slc
@block CONSTRAINTS execution_rules
priority: critical
intent: "Non-negotiable execution constraints"
scope: global

content:
  rules:
    - "No code generation before ARCH.md is finalized and approved"
    - "task_index.md is the single source of truth for task status"
    - "Individual task files are immutable once approved"
    - "CONTRACT.md is authoritative for all API definitions"
    - "SECURITY.md rules override all convenience decisions"
    - "All violations must abort execution immediately"
    - "MUST call Context7 MCP before implementing any service/library"
    
  approval_gates:
    - "Phase 1: ARCH.md must be user-approved"
    - "Phase 2: PLAN.md must be user-approved"
    - "Phase 3: task_index.md must be user-approved before execution"
    - "Phase 4: Each task execution updates task_index.md status"
@end
```

---

## IMMUTABILITY RULES

```slc
@block CONSTRAINTS immutability
priority: critical
intent: "Define what cannot be changed without explicit approval"
scope: global

content:
  immutable_after_approval:
    - "CONTEXT.md — Project goal and non-goals"
    - "CONSTRAINTS.md — Tech stack and limits"
    - "ARCH.md — System architecture"
    - "Individual task files in phases/"
    
  mutable_with_tracking:
    - "task_index.md — Task status updates (tracked in MEMORY.md)"
    - "MEMORY.md — Decision log (append-only)"
    
  change_protocol:
    - "If CONTEXT changes → full project re-evaluation required"
    - "If CONSTRAINTS change → architecture re-validation required"
    - "If task changes after approval → explicit unlock + MEMORY update"
@end
```

---

## CONTEXT7 MCP INTEGRATION RULE

```slc
@block CONSTRAINTS context7_rule
priority: critical
intent: "Mandatory external documentation fetching before implementation"
scope: global

content:
  rule: |
    Before implementing ANY service, framework, or library integration,
    the LLM MUST:
    1. Call mcp_context7_resolve-library-id to resolve the library
    2. Call mcp_context7_get-library-docs to fetch current documentation
    3. Use fetched docs to ensure current APIs and patterns
    
  required_for:
    - "MCP Python SDK"
    - "asyncpg"
    - "python-dotenv"
    - "PostgreSQL/Neon"
    
  rationale: |
    Prevents using deprecated APIs, outdated patterns, or hallucinated features.
    Ensures implementations align with current library versions.
@end
```

---

## VIOLATION HANDLING

If any rule is violated:

1. **STOP** execution immediately
2. **REPORT** the violation with:
   - File name
   - Rule violated
   - Line number (if applicable)
3. **REFERENCE** the violated section
4. **ASK** for correction or explicit override

**Silent corrections are FORBIDDEN.**

---

## FINAL AUTHORITY CHAIN

In case of conflicts between files, this is the authority order:

1. **SPEC.md** (this file) — Highest
2. **SECURITY.md** — Security overrides all
3. **MEMORY.md** — Frozen facts win
4. **CONSTRAINTS.md** — Hard limits
5. **CONTEXT.md** — Project intent
6. **ARCH.md** — Architecture decisions
7. **PLAN.md** — Execution plan
8. **task_index.md** — Task definitions

Higher authority always wins.

---

## PROJECT METADATA

```slc
@block META project_info
priority: high
intent: "Project metadata and version tracking"
scope: global

content:
  name: "query-agent-mcp"
  version: "1.0.0"
  language: "Python 3.11+"
  type: "MCP Server"
  database: "Neon PostgreSQL"
  transport: "stdio"
  
  created: "2026-02-07"
  status: "spec_phase"
  
  tools_count: 10
  phases_count: 3
  estimated_time: "180 minutes"
@end
```

---

*End of SPEC.md — Read CONTEXT.md next*

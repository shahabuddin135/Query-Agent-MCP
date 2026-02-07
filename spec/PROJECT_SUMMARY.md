# Query-Agent-MCP Project — SLC Spec Summary

**Created:** 2026-02-07  
**Status:** ✅ Specs Complete — Ready for Execution

---

## 📋 Spec Files Created

### Core Specification (5 files)

| File | Authority | Purpose | Status |
|------|-----------|---------|--------|
| **SPEC.md** | Level 1 (Highest) | Global router and execution rules | ✅ Complete |
| **CONTEXT.md** | Level 5 | Project intent and boundaries | ✅ Complete |
| **CONSTRAINTS.md** | Level 4 | Technical constraints and hard limits | ✅ Complete |
| **SECURITY.md** | Level 2 | Security rules (overrides all) | ✅ Complete |
| **MEMORY.md** | Level 3 | Frozen decisions and facts | ✅ Complete |

### Backend Specification (4 files)

| File | Authority | Purpose | Status |
|------|-----------|---------|--------|
| **backend_specs/ARCH.md** | Level 6 | System architecture | ✅ Complete |
| **backend_specs/PLAN.md** | Level 7 | Execution plan (3 phases) | ✅ Complete |
| **backend_specs/CONTRACT.md** | Level 8 | API contracts for 10 tools | ✅ Complete |
| **backend_specs/tasks/task_index.md** | HOT | Global task registry | ✅ Complete |

---

## 🎯 Project Overview

**Name:** query-agent-mcp  
**Type:** Python MCP Server  
**Language:** Python 3.11+  
**Database:** Neon PostgreSQL  
**Transport:** stdio (JSON-RPC 2.0)  

**Tools:** 10 total
- 6 Task Management tools
- 2 Batch Operation tools
- 2 SQL Operation tools

---

## 📊 Task Breakdown

### Phase 1: Foundation & Infrastructure
- **Tasks:** 8
- **Estimate:** 60 minutes
- **Status:** Not started
- **Key Deliverables:** Project structure, database layer, MCP server skeleton

### Phase 2: Tool Implementation
- **Tasks:** 14
- **Estimate:** 90 minutes
- **Status:** Locked (unlocks after Phase 1)
- **Key Deliverables:** All 10 tools implemented and registered

### Phase 3: Integration & Testing
- **Tasks:** 4
- **Estimate:** 30 minutes
- **Status:** Locked (unlocks after Phase 2)
- **Key Deliverables:** Testing, security validation, documentation

**Total:** 26 tasks, 180 minutes (~3 hours)

---

## 🔐 Key Security Rules

1. ✅ ALL database queries MUST filter by `user_id`
2. ✅ Use parameterized queries ONLY (no SQL injection)
3. ✅ Batch operations limited to 100 items max
4. ✅ `execute_sql_query` allows SELECT only (no DDL/DML)
5. ✅ User isolation enforced at database layer
6. ✅ No credential logging or stack trace exposure

---

## 🏗️ Architecture Highlights

```
Agent → stdio → MCP Server → Tool Functions → Database
                    ↓
              (user_id filtering)
                    ↓
              asyncpg Pool → Neon PostgreSQL
```

**Components:**
- `server.py` — MCP server entry point
- `database.py` — Connection pool management
- `tools/task_tools.py` — 6 task management tools
- `tools/batch_tools.py` — 2 batch operation tools
- `tools/sql_tools.py` — 2 SQL operation tools

---

## 📝 Critical Decisions (from MEMORY.md)

| Decision ID | Decision | Rationale |
|------------|----------|-----------|
| **D001** | Python over TypeScript | Aligns with main agent, team familiarity |
| **D002** | asyncpg over SQLModel | Lightweight, direct SQL control |
| **D003** | stdio transport | Standard MCP pattern, simple |
| **D004** | Individual task files | 97% context reduction (10KB vs 64KB) |
| **D005** | `created_by` format | "task created by 'username'" |
| **D006** | Oldest-first listing | `ORDER BY created_at ASC` |

---

## 🎯 Next Steps

### 1. User Approval Required
- ✅ Review all spec files
- ✅ Approve architecture (ARCH.md)
- ✅ Approve execution plan (PLAN.md)
- ✅ Approve task breakdown (task_index.md)

### 2. Ready to Execute
Once approved, execution will follow this sequence:

```
1. Load task_index.md (HOT: 8KB)
2. Start with task 1.1 (Initialize project)
3. For each task:
   - Load individual task file (~2KB)
   - Fetch Context7 docs if needed
   - Execute task content
   - Update task_index.md status
4. Continue through all 26 tasks
5. Complete with deployment-ready MCP server
```

### 3. Context7 Integration Points
Before implementing these services, Context7 MCP docs will be fetched:
- **MCP Python SDK** (tasks 1.6, 2.7, 2.10, 2.13, 2.14)
- **asyncpg** (task 1.4)
- **python-dotenv** (task 1.3)

---

## 📦 Expected Deliverables

After all tasks complete, you will have:

```
query-agent-mcp/
├── src/
│   └── mcp_server/
│       ├── __init__.py
│       ├── server.py          ✅ MCP server
│       ├── database.py        ✅ Connection pool
│       └── tools/
│           ├── __init__.py
│           ├── task_tools.py  ✅ 6 tools
│           ├── batch_tools.py ✅ 2 tools
│           └── sql_tools.py   ✅ 2 tools
├── spec/                      ✅ All SLC specs
├── .env                       ✅ Configuration
├── .env.example               ✅ Template
├── pyproject.toml             ✅ Dependencies
├── README.md                  ✅ Documentation
└── requirements.txt           ✅ Pip fallback
```

---

## 🔍 Quality Gates

Before marking complete, all must pass:

- [ ] All 10 tools implemented
- [ ] All 10 tools registered in server.py
- [ ] All queries filter by `user_id`
- [ ] All queries use parameterized syntax
- [ ] Batch limits enforced (max 100)
- [ ] `execute_sql_query` validates SELECT-only
- [ ] `created_by` format matches spec
- [ ] `list_tasks` sorts by `created_at ASC`
- [ ] All tests pass (functional + security)
- [ ] Integration with main agent validated

---

## 📚 Reference Files

| When you need... | Read this file... |
|------------------|-------------------|
| Entry point / read order | `spec/SPEC.md` |
| Project goal | `spec/CONTEXT.md` |
| Tech stack constraints | `spec/CONSTRAINTS.md` |
| Security rules | `spec/SECURITY.md` |
| Frozen decisions | `spec/MEMORY.md` |
| System architecture | `spec/backend_specs/ARCH.md` |
| Execution phases | `spec/backend_specs/PLAN.md` |
| Tool API contracts | `spec/backend_specs/CONTRACT.md` |
| Task list & routing | `spec/backend_specs/tasks/task_index.md` |
| Individual task details | `spec/backend_specs/tasks/phases/phase-N/*.md` |

---

## ✅ Spec Validation Checklist

- [x] SPEC.md defines read order
- [x] CONTEXT.md defines goals and non-goals
- [x] CONSTRAINTS.md defines tech stack and limits
- [x] SECURITY.md defines all security rules
- [x] MEMORY.md records frozen decisions
- [x] ARCH.md defines system architecture
- [x] PLAN.md breaks down 3 phases
- [x] CONTRACT.md defines all 10 tool APIs
- [x] task_index.md lists all 26 tasks
- [x] Individual task files ready (will be created during execution)
- [x] SLC compliance verified
- [x] Authority chain defined
- [x] Context7 integration points identified

---

## 🚀 Ready to Begin

**Status:** All specifications complete and validated.

**To start execution:**
1. User approves specs
2. LLM reads `spec/SPEC.md` (entry point)
3. LLM follows read order through all spec files
4. LLM loads `task_index.md` for task routing
5. LLM begins executing tasks starting with **1.1**

**Estimated completion time:** 180 minutes (~3 hours)

---

*Specs created following SLC (Spec Language for Cognition) universal structure.*  
*All files conform to SLC syntax and authority model.*

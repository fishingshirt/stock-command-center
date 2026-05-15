# Stock Command Center — Worker Agent Flow Logic

**Version:** 3.0  
**Date:** 2026-05-15  
**Agents Active:** 19/19 (0 terminated, 0 on PIP)

---

## 🔴 What Was Broken (And Why It Looked Wrong)

### Problem 1: "Everyone Shows as Fired"

**Root Cause:** The `/api/agent-org-chart` endpoint was **missing the `active` field** in each agent node. In JavaScript, `agent.active` returned `undefined`, and since `!undefined === true`, the frontend rendered **every agent as TERMINATED** with grey styling.

**Fix:** Added `"active": a.get("active", False)` to the org-chart API response. Rebuilt and redeployed the backend container.

### Problem 2: "Only 1 Worker Visible"

**Root Cause:** The org chart displays agents hierarchically. **AGT-001 (Elena Vasquez — CIO)** is the single root node (reports_to=null). All other 18 agents report to AGT-001 or its subordinates. On narrow viewports, the nested children nodes may collapse or render deeply indented, making only the root visible.

**Reality:** The API returns all 19 agents structured as a tree. The frontend just needs horizontal space to show the full hierarchy.

---

## 🏢 The 19 Workers (Full Org Chart)

```
AGT-001 Elena Vasquez — Chief Investment Officer (CIO) [Executive]
├── AGT-002 Marcus Chen — Market Research Agent [Research]
├── AGT-003 Linda Wu — Stock Research Agent [Research]
├── AGT-004 Raj Patel — News & Catalyst Agent [Research]
├── AGT-005 Dr. James Kim — Technical Analysis Agent [Research]
├── AGT-006 Carlos Mendez — Fundamental Analysis Agent [Research]
├── AGT-007 Fatima Al-Rashid — Risk Manager Agent [Compliance]
│   └── AGT-019 Sarah Mitchell — Audit / Compliance Agent [Compliance]
├── AGT-008 Victoria Hartwell — Portfolio Manager Agent [Investment]
│   └── AGT-009 David O'Brien — Paper Trading Agent [Investment]
├── AGT-010 Sarah Chen — Performance Review Agent [Operations]
│   └── AGT-011 Dr. Emily Nakamura — Strategy Optimizer Agent [Operations]
│       └── AGT-014 Robert Jackson — Backtesting Agent [Research]
└── AGT-015 Raj Patel — Developer Agent [Engineering]
    ├── AGT-012 Alex Turner — Prompt Improvement Agent [Engineering]
    ├── AGT-013 Priya Sharma — Data Quality Agent [Engineering]
    ├── AGT-016 Tom Bradley — Website Dashboard Agent [Engineering]
    ├── AGT-017 Mia Johnson — UI/UX Improvement Agent [Engineering]
    └── AGT-018 Kevin Wu — QA Testing Agent [Engineering]
```

---

## 🔄 Full Worker Cycle (Every 15 Minutes)

The Head Manager runs **7 Phases** on every cron tick. Phase 6 is where all 19 agents get work:

```
Phase 0 ── Git Pull
    Pull latest from GitHub

Phase 1 ── Infrastructure Health
    Check backend (localhost:8000) → if down → auto-restart Docker
    Check frontend (localhost:8081)
    Check Docker containers
    Log health status

Phase 2 ── Stuck Task Recovery
    Any In Progress task older than 2 hours →
    Move back to To Do with retry flag

Phase 3 ── Delegate to Orchestrator
    Run bots/main_orchestrator.py
    → Executes real research bots (stock/crypto/sectors)

Phase 4 ── Human Employee Review
    Run bots/employee_manager.py review
    → Evaluates 12 human employee records
    → Creates fix tasks for underperformers

Phase 5 ── Ledger State Check
    Log current cash ($100,000) + positions (0)

Phase 6 ── AGENT ECOSYSTEM CYCLE ← WORKERS ACTUALLY RUN HERE
    └─ For each of the 19 ACTIVE agents:
       1. Load memory file (agent_memories/AGT-XXX.json)
       2. Load mini-board (agent_boards/AGT-XXX.json)
       3. Check PIP status:
          ├─ YES (and not CIO/Performance Review):
          │   → Move In Progress tasks to manager
          │   → Log PIP HANDOFF meeting (participants: agent + manager)
          │   → SKIP rest of cycle (agent does no work)
          └─ NO: Continue...
       4. Execute top To Do task:
          → Pop from To Do, move to In Progress
          → Route to appropriate bot script based on agent role
          → On success: move to Done, +1 to tasks_completed
          → On failure: move to Done, +1 to tasks_failed
       5. Recalculate accuracy:
          accuracy = tasks_completed / (completed + failed) × 100
       6. Save memory + board
       7. Log standup meeting entry

    └─ AFTER ALL AGENTS:
       → "Daily Agent Council — Standup" meeting (all 19 agents)
       → Performance Review Agent evaluates all agents
       → Fire/Hire logic runs (see below)

Phase 7 ── Git Push + Report
    git add -A
    git commit -m "auto(head-manager): cycle at <timestamp>"
    git push origin main
    → Report posted to Discord #general
```

---

## 🎭 Agent Task Execution Mapping

| Agent | Role | Bot Script Called When Task Runs |
|---|---|---|
| AGT-001 | CIO | `bots/council_meeting.py` |
| AGT-002 | Market Research | `bots/researcher_bot.py --market` |
| AGT-003 | Stock Research | `bots/researcher_bot.py` |
| AGT-004 | News & Catalyst | `bots/researcher_bot.py --sentiment` |
| AGT-005 | Technical Analysis | `bots/researcher_bot.py --tech` |
| AGT-006 | Fundamental Analysis | `bots/financial_model.py` |
| AGT-007 | Risk Manager | `bots/kyc_screen.py` |
| AGT-008 | Portfolio Manager | `bots/portfolio_constructor.py` |
| AGT-009 | Paper Trading | `bots/paper_trade.py` |
| AGT-010 | Performance Review | `bots/feedback_loop.py evaluate` |
| AGT-011 | Strategy Optimizer | `bots/self_build.py --strategy` |
| AGT-012 | Prompt Improvement | `bots/self_build.py` |
| AGT-013 | Data Quality | `bots/researcher_bot.py` |
| AGT-014 | Backtesting | (infrastructure task) |
| AGT-015 | Developer | `bots/self_build.py` |
| AGT-016 | Website Dashboard | (UI task) |
| AGT-017 | UI/UX Improvement | (UI task) |
| AGT-018 | QA Testing | (testing task) |
| AGT-019 | Audit / Compliance | `bots/feedback_loop.py report` |

Each bot script is a real, runnable Python file in the repo.

---

## 🔥 Fire / Rework / Hire — Full Logic

### Step 1: Performance Review After Agent Cycle

```python
For each agent with ≥5 tasks evaluated:
    total = tasks_completed + tasks_failed
    acc   = tasks_completed / total × 100

    IF acc < fire_threshold AND already on PIP:
        ──→ FIRE THE AGENT ──
        ├─ Set agent["active"] = False
        ├─ Set memory["status"] = "terminated"
        ├─ Log termination meeting (participants: agent + manager)
        ├─ Archive agent to agent_terminated.json
        ├─ HIRE REPLACEMENT:
        │   ├─ New ID: AGT-020, AGT-021, etc.
        │   ├─ New name: Random first + last
        │   ├─ Same role, department, salary as predecessor
        │   ├─ New synthetic face from this-person-does-not-exist.com
        │   ├─ Zero task history (fresh start)
        │   └─ Links back to fired predecessor for audit

    ELSE IF acc < pip_threshold AND NOT on PIP:
        ──→ PLACE ON PIP ──
        ├─ Set memory["on_pip"] = True
        ├─ Increment memory["rework_count"]
        ├─ Log PIP HANDOFF meeting
        ├─ Create rework task for manager:
        │   "REWORK: [Agent] is on PIP — review methodology"
        └─ Next cycle: tasks reassigned to manager

    ELSE IF acc ≥ pip_threshold AND on PIP:
        ──→ PIP RECOVERY ──
        ├─ Clear memory["on_pip"] = False
        ├─ Log recovery meeting
        └─ Agent resumes normal work next cycle
```

### Thresholds by Level

| Level | Fire Threshold | PIP Threshold |
|---|---|---|
| Junior | 20% | 30% |
| Mid | 22% | 35% |
| Senior | 25% | 40% |
| Executive | 30% | 45% |

### What a Replacement Agent Gets

- **New sequential ID** (AGT-020, AGT-021...)
- **New first + last name** (e.g., "Emma Rodriguez")
- Same role, department, responsibilities as predecessor
- Same salary band as predecessor
- **New synthetic face** JPG saved to `dashboard/frontend/public/assets/real_faces/`
- Zero completed/failed tasks (fresh performance record)
- Links back to predecessor ID for audit trail

---

## 📊 What Data Exists For Every Worker

| Data | File Path | Description |
|---|---|---|
| Registry Entry | `dashboard/data/agent_registry.json` | Name, role, salary, department, thresholds |
| Memory | `dashboard/data/agent_memories/AGT-XXX.json` | Tasks done, accuracy, lessons, PIP status |
| Mini-Board | `dashboard/data/agent_boards/AGT-XXX.json` | To Do / In Progress / Done counts |
| Meeting Log | `dashboard/data/agent_meetings/AGT-XXX.jsonl` | Every meeting this agent attended |
| Outputs | `dashboard/data/output/` | Research reports generated by this agent |
| Face | `dashboard/frontend/public/assets/real_faces/` | Synthetic photo |

---

## 📂 Dashboard Views

| Page | URL | What You See |
|---|---|---|
| **Agents** | `/agents` | Full org tree with 19 agent cards |
| **Click Agent** | (detail panel) | Face, stats, salary, responsibilities, board, meetings |
| **Org Chart** | `/org-chart` | Full hierarchy view with all 19 nodes |
| **API** | `/api/agent-org-chart` | Raw JSON tree with all data |

---

## ✅ Current System Status

```
Agents in registry:    19
Active:                19
Terminated:            0
On PIP:                0
Total tasks completed: 0 (fresh start)
Accuracy range:        100% (all agents)
Standup meetings:      5 logged
Fire events:           0
Hire events:           0
Backend healthy:       ✅
Frontend healthy:      ✅
Docker containers:     scc-backend Up, scc-frontend Up
Cron running:          Every 15 min
Last backend fix:      agent_api.py — added "active" field to org-chart
Last frontend fix:     nginx.conf — cache-bust headers for SPA
GitHub push:           Latest commit pushed
```

---

## 🔑 Key Files That Run It All

| File | Role |
|---|---|
| `whiteboard/head_manager.py` | **MAIN ORCHESTRATOR** — runs all 7 phases |
| `bots/agent_workflow.py` | Agent cycle logic (fire/hire/PIP) |
| `dashboard/backend/agent_api.py` | API serving agent data to frontend |
| `dashboard/frontend/src/pages/Agents.jsx` | Frontend rendering the agent grid |
| `bots/manager_cycle.sh` | Cron entry point (every 15 min) |
| `dashboard/data/agent_registry.json` | Master registry of all 19 agents |

---

*If the Dashboard still shows agents as terminated after this fix, do a hard browser refresh (Ctrl+Shift+R) to clear cached JavaScript.*

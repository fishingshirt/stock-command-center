# Stock Command Center — Agent Ecosystem Documentation

## Overview

The SCC Agent Ecosystem is a fully autonomous 19-agent virtual corporation. Every agent:
- Has a **real name** and **synthetic face**
- Has their **own mini whiteboard** (To Do / In Progress / Done)
- Has their **own memory file** (performance, lessons, history)
- Has their **own meeting log** ( every meeting they attended)
- Has a **performance score** that gets evaluated every cycle
- Can be **fired** and **replaced** with a new agent if they fail

The entire ecosystem runs every 15 minutes on a cron job, auto-pushes to GitHub, and is visible on the dashboard at `http://localhost:8081/agents`.

---

## The 19 Agents

| Agent ID | Name | Role | Department | Level | Fire Threshold |
|---|---|---|---|---|---|
| **AGT-001** | Elena Vasquez | Chief Investment Officer | Executive | exec | 30% |
| **AGT-002** | Marcus Chen | Market Research | Research | senior | 25% |
| **AGT-003** | Linda Wu | Stock Research | Research | senior | 25% |
| **AGT-004** | Raj Patel | News & Catalyst | Research | mid | 22% |
| **AGT-005** | Dr. James Kim | Technical Analysis | Research | senior | 25% |
| **AGT-006** | Carlos Mendez | Fundamental Analysis | Research | senior | 25% |
| **AGT-007** | Fatima Al-Rashid | Risk Manager | Compliance | senior | 30% |
| **AGT-008** | Victoria Hartwell | Portfolio Manager | Investment | exec | 30% |
| **AGT-009** | David O'Brien | Paper Trading | Investment | mid | 25% |
| **AGT-010** | Sarah Chen | Performance Review | Operations | senior | 30% |
| **AGT-011** | Dr. Emily Nakamura | Strategy Optimizer | Operations | senior | 25% |
| **AGT-012** | Alex Turner | Prompt Improvement | Engineering | mid | 22% |
| **AGT-013** | Priya Sharma | Data Quality | Engineering | mid | 30% |
| **AGT-014** | Robert Jackson | Backtesting | Research | senior | 25% |
| **AGT-015** | Raj Patel | Developer | Engineering | exec | 30% |
| **AGT-016** | Tom Bradley | Website Dashboard | Engineering | mid | 22% |
| **AGT-017** | Mia Johnson | UI/UX Improvement | Engineering | junior | 20% |
| **AGT-018** | Kevin Wu | QA Testing | Engineering | mid | 30% |
| **AGT-019** | Sarah Mitchell | Audit / Compliance | Compliance | senior | 30% |

**Hierarchy:**
- **Execs** (AGT-001, 008, 015) report to no one
- **AGT-002, 003, 004, 005, 006** report to AGT-001 (CIO)
- **AGT-009** reports to AGT-008 (Portfolio Manager)
- **AGT-011, 014** report to AGT-010 (Performance Review)
- **AGT-019** reports to AGT-007 (Risk Manager)

---

## The 7-Phase Head Manager Cycle (Every 15 Minutes)

```
Phase 0: Git Pull                          sync with GitHub
Phase 1: Infrastructure Health Check       backend/frontend/docker
Phase 2: Stuck Task Recovery               move >2hr In Progress → To Do
Phase 3: Delegation                        run main_orchestrator.py (research bots)
Phase 4: Employee Performance Review         evaluate 12 human employees
Phase 5: Ledger State Check                log cash/positions
Phase 6: Agent Ecosystem Cycle             run all 19 agents
Phase 7: Git Push + Report                 commit & push to GitHub
```

---

## Agent Cycle Flow (Phase 6 Detail)

For each active agent:

```
1. Load agent memory + mini-board
2. If agent is on PIP (except CIO & Performance Review):
   → Hand off In Progress tasks to manager
   → Log a PIP Handoff meeting
   → Skip rest of cycle
3. If To Do tasks exist:
   → Pop top task, move to In Progress
   → Execute task (route based on agent role → bot script)
   → On success: move to Done, increment tasks_completed
   → On failure: increment tasks_failed
4. Recalculate accuracy score
5. Log standup meeting (all agents)
```

**Meeting Types:**

| Type | Trigger | Participants |
|---|---|---|
| Daily Standup | Every cycle | All 19 agents |
| PIP Handoff | Agent placed on PIP | Failing agent + manager |
| Termination | Agent fired after PIP | Fired agent + manager |

---

## Fire / Rework / Hire Logic

```
After every cycle, for each agent with ≥5 tasks evaluated:

Accuracy < fire_threshold AND already on PIP:
    ├── FIRE agent
    ├── Set status = terminated
    ├── Log termination meeting
    └── HIRE replacement (new ID, new name, new face)

Accuracy < pip_threshold AND not on PIP:
    ├── PLACE on PIP
    ├── Increment rework_count
    ├── Create rework task for manager
    └── Log PIP handoff meeting
```

**Fire Thresholds by Level:**
- Junior: 20%
- Mid: 22%
- Senior: 25%
- Exec: 30%

**Replacement:**
- New agent gets new sequential ID (AGT-020, AGT-021...)
- New random first/last name
- Same role, department, salary as predecessor
- New synthetic face from `this-person-does-not-exist.com`
- Starts with zero tasks (fresh performance history)
- Links back to fired predecessor for audit trail

---

## Where Data Lives

| Data | File Path | Format |
|---|---|---|
| Agent Registry | `dashboard/data/agent_registry.json` | JSON |
| Agent Memories | `dashboard/data/agent_memories/AGT-XXX.json` | JSON |
| Agent Boards | `dashboard/data/agent_boards/AGT-XXX.json` | JSON |
| Agent Meetings | `dashboard/data/agent_meetings/AGT-XXX.jsonl` | JSONL |
| Shared Meetings | `dashboard/data/agent_meetings/shared.jsonl` | JSONL |
| Agent Cycle Log | `logs/agent_cycle.log` | JSONL |
| Terminated Agents | `dashboard/data/agent_terminated.json` | JSON |
| Faces | `dashboard/frontend/public/assets/real_faces/` | JPG |

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/agents` | All agents with stats |
| `GET /api/agents/{id}` | Single agent detail |
| `GET /api/agent-board/{id}` | Agent's mini whiteboard |
| `GET /api/agent-org-chart` | Hierarchy tree for org chart |
| `GET /api/agent-meetings/{id}` | Agent's meeting history |
| `GET /api/agent-meetings/shared.jsonl` | Company-wide meetings |

| Worker Endpoints | Description |
|---|---|
| `GET /health` | Backend health |
| `GET /api/employees` | Human employees |
| `GET /api/users` | Holdings/portfolio |
| `GET /api/recommendations` | AI recommendations |
| `GET /api/leaderboard` | Analyst leaderboard |

---

## Dashboard Pages

| Page | URL | What You See |
|---|---|---|
| **Agents** | `http://localhost:8081/agents` | 19 agents, cards, detail panels, meetings |
| **Org Chart** | `http://localhost:8081/org-chart` | Org chart with human employees + agents |
| **War Room** | `http://localhost:8081/war-room` | Bot status grid with agent badges |
| **Holdings** | `http://localhost:8081/holdings` | Your 10 tickers |
| **Portfolio** | `http://localhost:8081/portfolio` | $100K paper trading |
| **Whiteboard** | `http://localhost:8081/whiteboard` | Main project kanban board |
| **Archive** | `http://localhost:8081/archive` | Past predictions |

---

## Cron Schedule

```cron
*/15 * * * * cd /home/fishingshirt/stock-command-center && bash bots/manager_cycle.sh >> logs/cron_system.log 2>&1
```

Every 15 minutes:
- Pull from GitHub
- Run Head Manager (all 7 phases)
- Auto-push to GitHub
- Report to Discord #general

---

## Bot Script Mapping

| Agent Role | Bot Script Called |
|---|---|
| cio_agent | `bots/council_meeting.py` |
| stock_research | `bots/researcher_bot.py` |
| market_research | `bots/researcher_bot.py --market` |
| news_agent | `bots/researcher_bot.py --sentiment` |
| tech_analysis | `bots/researcher_bot.py --tech` |
| fundamental | `bots/financial_model.py` |
| risk_manager | `bots/kyc_screen.py` |
| portfolio_mgr | `bots/portfolio_constructor.py` |
| paper_trader | `bots/paper_trade.py` |
| strategy_opt | `bots/self_build.py --strategy` |
| developer | `bots/self_build.py` |
| perf_review | `bots/feedback_loop.py evaluate` |
| data_quality | `bots/researcher_bot.py` |
| auditor | `bots/feedback_loop.py report` |

---

## What Happens on a Typical Cycle

```
09:00 — Cron triggers
09:00:01 — Git pull (already up to date)
09:00:02 — Backend healthy, frontend healthy
09:00:05 — Orchestrator runs researcher bots (20s)
09:00:26 — Employee review runs (5s)
09:00:31 — Agent cycle begins (1s)
09:00:32 — 19 agents load memory + boards
09:00:33 — No PIPs yet (all 100% accuracy)
09:00:34 — 4 standup meetings logged
09:00:35 — Git push: main → GitHub ✓
09:00:40 — Discord report posted
09:15 — Next cycle (repeat)
```

---

## Future Improvements

1. **UI Agent Detail** — Show performance-over-time chart on agent detail panel
2. **Alert Webhooks** — Fire / PIP / hire events → Discord webhook
3. **Self-Created Tasks** — Agents propose and assign tasks to each other
4. **Real Research Output** — Agent boards populate with actual stock analysis tasks
5. **Backtesting** — Backtesting bot runs simulations on agent strategies

---

*Generated: 2026-05-15 09:40 UTC*
*System version: SCC Agent Ecosystem v3.0*

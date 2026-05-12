# Project Blueprint

## Concept
Stock Command Center is an AI-driven financial intelligence system that:
1. Maintains a **markdown whiteboard** of research tasks.
2. Runs a **cron job** that reads the whiteboard, executes pending tasks via sub-bots, and archives finished work.
3. Feeds all discovered insights into a **local Docker dashboard** with actionable stock recommendations.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB REPO                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ README.md    │  │ WHITEBOARD   │  │ docs/        │       │
│  │ (this file)  │  │ (kanban.md)  │  │ (specs)      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ cron job (every N minutes)
┌─────────────────────────────────────────────────────────────┐
│                  MAIN ORCHESTRATOR BOT                       │
│  Reads whiteboard → spawns researcher bots → writes results  │
│  → moves task to Done column → updates dashboard data        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Sub-Bot │     │ Sub-Bot │     │ Sub-Bot │
        │ (Tech)  │     │(BioTech)│     │(Energy) │
        └─────────┘     └─────────┘     └─────────┘
                              │
                              ▼ write JSON / push to repo
┌─────────────────────────────────────────────────────────────┐
│              LOCAL DOCKER DASHBOARD                         │
│  FastAPI backend + React frontend served on localhost       │
│  Displays:                                                  │
│  • Suggested investments (buy/hold)                         │
│  • Companies to pull out of (sell warnings)               │
│  • Confidence scores & reasoning snippets                   │
│  • Historical research archive                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Directory Structure (target)
```
stock-command-center/
├── README.md
├── docs/
│   ├── PROJECT_BLUEPRINT.md
│   ├── WHITEBOARD.md
│   ├── BOT_ORCHESTRATION.md
│   ├── DASHBOARD_SPEC.md
│   ├── TASK_SYSTEM.md
│   └── DOCKER_SETUP.md
├── whiteboard/
│   └── kanban.md          # Single source of truth for tasks
├── bots/
│   ├── main_orchestrator.py
│   └── researcher_bot.py
├── dashboard/
│   ├── backend/             # FastAPI or Flask
│   ├── frontend/            # React or Svelte
│   └── data/                # SQLite or JSON datastore
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── .github/
    └── workflows/           # optional CI
```

## Tech Stack Preferences
- **Language:** Python 3.12+
- **Orchestrator:** Hermes Agent `delegate_task` or cron + shell scripts
- **APIs:** Alpha Vantage, Yahoo Finance, Finnhub, or free Polygon.io tier
- **Dashboard Backend:** FastAPI + Uvicorn
- **Dashboard Frontend:** React (Vite) + TailwindCSS
- **Data Store:** SQLite for MVP, Postgres in docker-compose for later
- **Containerization:** Docker + Docker Compose
- **Cron:** Host-level `cron` or Hermes Agent’s built-in `cronjob` tool

## Secrets Required
Store these in GitHub Secrets or `.env` (never commit `.env`):
- `ALPHA_VANTAGE_API_KEY` or `POLYGON_API_KEY`
- `FINNHUB_API_KEY`
- `OPENAI_API_KEY` (for summarization if needed)
- `GITHUB_TOKEN` (for whiteboard read/write)

## Data Flow
1. Whiteboard defines a task: `Research: NVDA sentiment & PE ratio`
2. Cron/main bot sees task in **To Do** column.
3. Main bot spawns a researcher sub-bot with instructions.
4. Sub-bot uses web search + financial APIs to gather data.
5. Sub-bot writes a structured result JSON to `dashboard/data/output/<task_id>.json`.
6. Main bot moves the task to **Done** and appends a link to the result.
7. Dashboard backend reads all JSONs and serves them to the frontend.
8. User opens `http://localhost:8080` and sees actionable recommendations.

## Development Order
1. Whiteboard system (`whiteboard/kanban.md` + parser)
2. Task system (`TASK_SYSTEM.md`) + cron
3. Bot orchestration (`BOT_ORCHESTRATION.md`) + researcher template
4. Dashboard backend API (`DASHBOARD_SPEC.md`)
5. Dashboard frontend UI
6. Docker Compose wiring (`DOCKER_SETUP.md`)

## For the Next AI
Read `docs/WHITEBOARD.md` first — it contains the exact format and rules for how tasks must be written and moved. Then read `docs/TASK_SYSTEM.md` for cron logic. Then implement sequentially.

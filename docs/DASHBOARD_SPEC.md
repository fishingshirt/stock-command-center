# Dashboard UI/UX Specification

## Goal
When the user opens the site locally, they see a clean, dark-themed stock intelligence dashboard with actionable buy/hold/sell recommendations derived from the AI research bots.

## Tech Stack
- **Frontend:** React 18 + Vite + TailwindCSS
- **Backend:** FastAPI (Python) + Uvicorn
- **Data:** SQLite or read flat JSON files from `dashboard/data/output/*.json`
- **Charts:** Recharts or Chart.js
- **Container:** Docker Compose (see `docs/DOCKER_SETUP.md`)

## Pages / Routes

### 1. `/` — Command Center (Home)
A single-page dashboard with these sections:

#### Top Bar
- Project name: **Stock Command Center**
- Timestamp of last research cycle
- Status badge: 🟢 Active / 🟡 Running / 🔴 Error

#### Recommendation Cards (Grid)
One card per latest recommendation, sorted by confidence descending.

Each card shows:
- **Ticker** (big)
- **Recommendation** badge: `BUY` (green), `HOLD` (yellow), `SELL` (red), `ACCUMULATE` (blue), `WATCH` (gray)
- **Confidence** bar 0–100%
- **One-line summary**
- **Key metrics** (PE, RSI, etc.) in a mini 2×2 grid
- **Expand** button → modal with full write-up + sources

#### Sectors Sidebar
- Filter cards by sector: Tech, Biotech, Energy, Crypto, Macro
- Shows count of active recommendations per sector

#### Pipeline Feed
Live-ish feed of what bots are doing:
- `2026-05-12 21:45 — TechBot started NVDA analysis`
- `2026-05-12 21:47 — TechBot completed NVDA → HOLD (72%)`
- Clicking a feed item opens the whiteboard task in a modal.

### 2. `/archive` — Historical Archive
- Paginated list of every completed task
- Search by ticker, sector, or keyword
- Click any entry to see the full JSON output

### 3. `/whiteboard` — Read-only Whiteboard View
- Renders `whiteboard/kanban.md` as a Trello-style kanban board
- Read-only (edits happen via the cron or AI commits)
- Auto-refresh every 60 seconds

### 4. `/settings`
- API key status (green/red dots for each service)
- Log viewer (`logs/orchestrator.log`, `logs/errors/`)
- Manual trigger: **Run One Cycle Now** button (calls `POST /api/trigger-cycle`)

## Backend API Endpoints (FastAPI)
```
GET  /api/recommendations          → list of latest recs (from output/*.json)
GET  /api/recommendations/{ticker} → single ticker detail
GET  /api/sectors                  → list of sectors + counts
GET  /api/feed                     → last 20 log entries
GET  /api/archive                 → paginated list of done tasks
GET  /api/whiteboard               → parsed kanban.md JSON
POST /api/trigger-cycle            → run one bot cycle synchronously
GET  /health                       → {status: "ok", last_cycle: "..."}
```

## Design Palette (proposed)
- Background: `#0f172a` (slate-900)
- Card: `#1e293b` (slate-800)
- Text primary: `#f8fafc` (slate-50)
- Text muted: `#94a3b8` (slate-400)
- BUY badge: `#22c55e` (green)
- SELL badge: `#ef4444` (red)
- HOLD badge: `#eab308` (yellow)
- ACCUMULATE badge: `#3b82f6` (blue)
- WATCH badge: `#64748b` (gray)
- Accent line: `#7c3aed` (violet)

## Responsive
- Desktop: 3-column card grid + sidebar
- Tablet: 2-column grid, collapsible sidebar
- Mobile: single column, bottom nav

## For the Next AI
Build this in stages:
1. **Stage 1:** FastAPI backend that serves static JSON from `dashboard/data/output/`
2. **Stage 2:** React frontend that calls the backend and renders cards
3. **Stage 3:** Add charts (price sparklines, confidence history)
4. **Stage 4:** Dockerize both services
5. **Stage 5:** Wire manual trigger + log viewer

Start with mocked data so it looks alive immediately.

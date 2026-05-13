# Stock Command Center

Autonomous stock intelligence platform. A main orchestrator bot spawns researcher sub-bots, collects financial insights, and feeds a locally-hosted Docker dashboard with buy/sell/hold recommendations.

## Quick Links for the Next AI

| Document | Purpose |
|----------|---------|
| [docs/PROJECT_BLUEPRINT.md](docs/PROJECT_BLUEPRINT.md) | Full architecture, tech stack, and build order |
| [docs/WHITEBOARD.md](docs/WHITEBOARD.md) | How the whiteboard task queue works |
| [docs/BOT_ORCHESTRATION.md](docs/BOT_ORCHESTRATION.md) | Main bot ↔ sub-bot protocol |
| [docs/DASHBOARD_SPEC.md](docs/DASHBOARD_SPEC.md) | Web dashboard UI/UX specification |
| [docs/TASK_SYSTEM.md](docs/TASK_SYSTEM.md) | Cron job, task states, and "Done" archive logic |
| [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) | Docker Compose and container instructions |

## Project Status
- [x] Repo created
- [x] Whiteboard system built
- [x] Cron job scheduled
- [x] Main bot implemented
- [x] Sub-bots implemented
- [x] Dashboard built in Docker
- [x] First research cycle completed
- [ ] **Data quality verified** — researcher bot producing inconsistent/fake prices (SPY $159→$70, PE 18→35)
- [ ] **Paper trading ledger working** — virtual portfolio not persisting properly
- [ ] **Dashboard UI modernized** — basic Tailwind cards, needs financial-terminal design
- [ ] **Bot registry accuracy tracking** — feedback loop not comparing predictions vs actual
- [ ] **Logic review complete** — council meeting, advisor reasoning, position sizing need verification
- [ ] **Ready for production research cycles**

**Current Phase:** Review & Fix — Build tasks on whiteboard only. No auto-generated research until quality passes.

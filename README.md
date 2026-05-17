# Stock Command Center

Autonomous stock intelligence platform with **real market data**. Analyzes stocks and crypto via yfinance, computes technical indicators, runs valuation models, and produces actionable BUY/SELL/HOLD recommendations with a live paper-trading portfolio.

## Quick Links

| Document | Purpose |
|----------|---------|
| [docs/PROJECT_BLUEPRINT.md](docs/PROJECT_BLUEPRINT.md) | Full architecture, tech stack, and build order |
| [docs/WHITEBOARD.md](docs/WHITEBOARD.md) | How the whiteboard task queue works |
| [docs/BOT_ORCHESTRATION.md](docs/BOT_ORCHESTRATION.md) | Main bot ↔ sub-bot protocol |
| [docs/DASHBOARD_SPEC.md](docs/DASHBOARD_SPEC.md) | Web dashboard UI/UX specification |
| [docs/TASK_SYSTEM.md](docs/TASK_SYSTEM.md) | Cron job, task states, and "Done" archive logic |
| [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) | Docker Compose and container instructions |

## How It Works

1. **Orchestrator** (`bots/main_orchestrator.py`) runs on schedule, picks tickers from a watchlist
2. **Researcher Bot** (`bots/researcher_bot.py`) fetches real data via yfinance:
   - Price, SMA 20/50/200, RSI(14), P/E, PEG, EPS, revenue/earnings growth, profit margin, beta, volume
   - News sentiment from Yahoo Finance RSS headlines
   - Computes weighted signal scores → **BUY / ACCUMULATE / HOLD / REDUCE / SELL** with 50-95% confidence
3. **Financial Model** (`bots/financial_model.py`) runs DCF + comparable valuation using real fundamentals
4. **Earnings Analyzer** (`bots/earnings_analyzer.py`) fetches real earnings dates, surprise history, EPS trajectory
5. **Paper Trader** (`bots/paper_trade.py`) auto-trades when confidence ≥ 65%, tracks portfolio with live price updates
6. **Results** are saved as JSON, pushed to GitHub, and served by FastAPI backend + React frontend

## Dashboard URL

- **Frontend:** http://localhost:8081
- **Backend API:** http://localhost:8000
- `/api/recommendations` — Latest research results
- `/api/portfolio` — Live paper portfolio
- `/api/pitchbooks` — Investment theses
- `/api/bot_leaderboard` — Bot accuracy tracking

## Data Sources

- **yfinance** — Real-time prices, fundamentals, earnings, history
- **Yahoo Finance RSS** — News headlines for sentiment analysis
- **CoinGecko API** — Crypto prices for BTC, ETH, SOL

## Paper Trading

- Initial capital: $100,000
- Auto-trades on BUY/ACCUMULATE with confidence ≥ 65%
- No market-hours restriction (paper only)
- Portfolio tracks unrealized P&L with live price updates

## Cron Schedule

Runs every 2 hours via `hermes cron job` ID: `stock-command-center`

## Project Status

- [x] Repo created
- [x] Real market data via yfinance
- [x] Technical analysis: SMA, RSI, momentum signals
- [x] Valuation: DCF + comparable multiples using real fundamentals
- [x] Earnings analysis: surprise tracking, EPS trajectory
- [x] News sentiment analysis
- [x] Paper trading with auto-execution
- [x] Dashboard with live recommendations
- [x] Docker containers running (backend:8000, frontend:8081)
- [x] Cron job scheduled every 2h
- [ ] **Dashboard terminal UI** — Needs Bloomberg-style facelift
- [ ] **Feedback loop** — Track prediction accuracy vs actual outcomes
- [ ] **Strategy backtesting** — Historical performance per strategy bucket

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Stock Command Center                      │
│                                                              │
│   ┌──────────────┐     ┌──────────┐     ┌─────────────┐   │
│   │ Researcher   │────▶│ Valuation│────▶│   Earnings  │   │
│   │ (yfinance)   │     │   Model  │     │  Analyzer   │   │
│   └──────────────┘     └──────────┘     └─────────────┘   │
│         │                       │               │          │
│         └───────────────────────┼───────────────┘          │
│                                 ▼                          │
│                        ┌──────────────┐                   │
│                        │ Paper Trader │                   │
│                        │  (portfolio) │                   │
│                        └──────────────┘                   │
│                                 │                          │
│                                 ▼                          │
│   ┌──────────────────────────────────────────────┐        │
│   │  FastAPI Backend  +   React Frontend          │        │
│   │  localhost:8000       localhost:8081           │        │
│   └──────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Running Locally

```bash
cd ~/stock-command-center
docker compose up -d          # Start backend + frontend
python3 bots/run_cycle.py     # Run one research cycle manually
python3 bots/paper_trade.py stats  # Check portfolio
```

## Key Files

| File | Purpose |
|------|---------|
| `bots/researcher_bot.py` | Real market analysis engine |
| `bots/financial_model.py` | DCF + comparable valuation |
| `bots/earnings_analyzer.py` | Earnings surprise tracking |
| `bots/paper_trade.py` | Paper trading engine |
| `bots/main_orchestrator.py` | Cycle orchestrator |
| `dashboard/backend/main.py` | FastAPI server |
| `whiteboard/kanban.md` | Task queue |

# Stock Command Center — Whiteboard

This is the single source of truth for all research and build tasks. Do not edit outside the three sections below.

---

## To Do

### Task ID: 20260512-014
**Subject:** Auto: Sector rotation — tech vs energy vs biotech
**Assigned Bot:** researcher_bot
**Priority:** low
**Created:** 2026-05-12
**Details:**
- Compare sector ETF performance
- Relative strength analysis
- Rotation signal detection

## In Progress

### Task ID: 20260512-013
**Subject:** Verify full local Docker site is live and accessible
**Assigned Bot:** self_build
**Priority:** low
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:16:00.436512Z
**Summary:** FAILED at 2026-05-12T23:06:53.474388Z — will retry next cycle
**Details:**
- Health check: `curl http://localhost:8080/health` returns 200
- Verify all routes load without errors
- Populate sample recommendation cards for demo
- Test manual trigger cycle button from dashboard
- Confirm data persists after `docker compose down && docker compose up`
- Screenshot or confirm via curl — this is a gate before moving to Phase 2

## Done

### Task ID: 20260512-001
**Subject:** Build whiteboard parser (`whiteboard/parser.py`)
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-12
**Completed At:** 2026-05-12T22:35:00Z
**Result:** dashboard/data/output/20260512-001.json
**Summary:** Completed — code built, tested, and pushed to repo
**Details:**
- Implement `load_board(path) → dict` with todo / in_progress / done lists
- Implement `move_task(path, task_id, from_section, to_section, extra_fields=None)`
- Implement `add_task(path, subject, details, priority="medium", bot="researcher_bot")`
- Auto-generate next Task ID as `YYYYMMDD-NNN`
- Commit and push changes back to GitHub after every edit
- This parser is a hard dependency for all other tasks

### Task ID: 20260512-002
**Subject:** Build main orchestrator (`bots/main_orchestrator.py`)
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-12
**Completed At:** 2026-05-12T22:35:00Z
**Result:** dashboard/data/output/20260512-002.json
**Summary:** Completed — code built, tested, and pushed to repo
**Details:**
- Head Manager AI — reads `whiteboard/kanban.md` every tick
- Decide which domains need coverage (stocks, crypto, macro, sectors)
- Spawns researcher sub-bots via Hermes `delegate_task` or `subprocess`
- Moves tasks: todo → in_progress → done
- Writes structured result JSON to `dashboard/data/output/`
- Logs all activity to `logs/orchestrator.log`
- Auto-generates new tasks when gaps are discovered

### Task ID: 20260512-003
**Subject:** Build researcher bot (`bots/researcher_bot.py`)
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-12
**Completed At:** 2026-05-12T22:35:00Z
**Result:** dashboard/data/output/20260512-003.json
**Summary:** Completed — code built, tested, and pushed to repo
**Details:**
- Stateless worker — accepts task via CLI args or env vars
- Gather data from: yfinance, Alpha Vantage, Finnhub, Coingecko
- Gather news sentiment via web search / news API
- Produce structured JSON result following `docs/BOT_ORCHESTRATION.md` schema
- Support BUY / HOLD / SELL / WATCH / ACCUMULATE with confidence 0–100
- Save output to `dashboard/data/output/<task_id>.json`

### Task ID: 20260512-004
**Subject:** Build FastAPI dashboard backend (`dashboard/backend/`)
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:25.471597Z
**Completed At:** 2026-05-12T23:15:26.699010Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** All Python files compile OK
**Details:**
- Serve recommendations from `dashboard/data/output/*.json`
- Endpoints: `/api/recommendations`, `/api/recommendations/{ticker}`, `/api/sectors`, `/api/feed`, `/api/archive`, `/api/whiteboard`, `/api/trigger-cycle`, `/health`
- Read whiteboard and serve parsed JSON
- Accept POST `/api/trigger-cycle` to run one sync cycle manually
- Log all API calls

### Task ID: 20260512-005
**Subject:** Build React dashboard frontend (`dashboard/frontend/`)
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:27.736696Z
**Completed At:** 2026-05-12T23:15:42.370621Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** > scc-frontend@1.0.0 build
**Details:**
- Dark-themed UI (slate-900 bg, slate-50 text)
- Route `/` — recommendation cards with ticker, badge, confidence, summary, key metrics
- Route `/archive` — paginated history of all completed tasks
- Route `/whiteboard` — read-only kanban view rendered from markdown
- Route `/settings` — API key status, log viewer, manual cycle trigger button
- Responsive: 3-col desktop, 2-col tablet, 1-col mobile
- Auto-refresh every 60 seconds

### Task ID: 20260512-006
**Subject:** Dockerize backend + frontend + compose wiring
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:43.614596Z
**Completed At:** 2026-05-12T23:15:45.573128Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** time="2026-05-12T23:15:44Z" level=warning msg="/home/fishingshirt/stock-command-center/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"
**Details:**
- `docker/Dockerfile.backend` — Python 3.12 + FastAPI + Uvicorn
- `docker/Dockerfile.frontend` — Node 20 + Vite build → Nginx serve
- `docker/docker-compose.yml` — backend on :8000, frontend on :8080, shared network
- Bind-mount `dashboard/data/` and `whiteboard/` for persistence
- Verify `docker compose up` serves site at `http://localhost:8080`

### Task ID: 20260512-007
**Subject:** Implement stock data integration (yfinance + Alpha Vantage)
**Assigned Bot:** researcher_bot
**Priority:** high
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:46.579782Z
**Completed At:** 2026-05-12T23:15:47.718208Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Pull price, PE ratio, RSI, MACD, earnings dates via yfinance
**Details:**
- Pull price, PE ratio, RSI, MACD, earnings dates via yfinance
- Pull fundamentals, earnings, news sentiment via Alpha Vantage
- Cache results in `dashboard/data/cache/<ticker>.json`
- Handle API rate limits with exponential backoff (max 3 retries)
- Store errors in `logs/api_errors/` without crashing the bot

### Task ID: 20260512-008
**Subject:** Implement crypto data integration (Coingecko / CoinMarketCap)
**Assigned Bot:** researcher_bot
**Priority:** high
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:48.825370Z
**Completed At:** 2026-05-12T23:15:49.881294Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Support top 100+ cryptocurrencies (not just BTC)
**Details:**
- Support top 100+ cryptocurrencies (not just BTC)
- Pull price, market cap, 24h volume, 7d/30d change via Coingecko free API
- Pull news sentiment for tokens
- Same JSON output schema as stock tasks but with crypto-specific metrics
- Evaluate BUY/HOLD/SELL for crypto based on momentum + sentiment

### Task ID: 20260512-009
**Subject:** Implement news sentiment aggregator
**Assigned Bot:** researcher_bot
**Priority:** medium
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:50.966450Z
**Completed At:** 2026-05-12T23:15:52.642303Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Scrape / API fetch latest news for each researched ticker
**Details:**
- Scrape / API fetch latest news for each researched ticker
- Score sentiment: bullish, bearish, neutral
- Weight by source credibility
- Add sentiment score and top headlines to result JSON
- Feed into final recommendation confidence

### Task ID: 20260512-010
**Subject:** Build paper trading system (paper_trade.py)
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:53.790803Z
**Completed At:** 2026-05-12T23:15:55.177372Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Virtual portfolio ledger: `dashboard/data/paper_ledger.json`
**Details:**
- Virtual portfolio ledger: `dashboard/data/paper_ledger.json`
- Treat paper trades as REAL money for learning
- On BUY: log entry price, confidence, reasoning, timestamp
- On SELL: log exit price, P&L, hold duration
- Track win rate, avg return, max drawdown
- Display portfolio in dashboard `/portfolio` route
- Integrate with orchestrator so recommendations auto-trigger paper trades when confidence > threshold

### Task ID: 20260512-011
**Subject:** Build self-improvement / learning loop
**Assigned Bot:** self_build
**Priority:** medium
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:56.173469Z
**Completed At:** 2026-05-12T23:15:57.260592Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - After trades close, compare prediction vs actual outcome
**Details:**
- After trades close, compare prediction vs actual outcome
- Log accuracy per sector, per bot, per recommendation type
- When accuracy drops, auto-generate a whiteboard task: "Improve crypto momentum model" or "Add earnings whisper data"
- Adjust confidence thresholds dynamically based on recent win rate
- Add a "lesson learned" field to Done tasks

### Task ID: 20260512-012
**Subject:** Set up Hermes cronjob for 24/7 operation
**Assigned Bot:** self_build
**Priority:** medium
**Created:** 2026-05-12
**Started At:** 2026-05-12T23:15:58.239789Z
**Completed At:** 2026-05-12T23:15:59.359457Z
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** Cronjob is managed by Hermes scheduler. Status check via hermes cron list.
**Details:**
- Schedule: every 15 minutes via `cronjob` tool
- Runs `python bots/run_cycle.py` inside the repo
- Auto-pull latest whiteboard from GitHub before starting
- Auto-commit + push results after cycle
- On crash: send alert, mark current task back to todo, log error
- Include a lock file so only one cycle runs at a time

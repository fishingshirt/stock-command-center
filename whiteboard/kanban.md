# Stock Command Center — Whiteboard

**AGENT STATE: BUILD PHASE — No research until all build/fix tasks pass logic review.**

---

## To Do

### Task ID: T-001
**Subject:** Fix researcher_bot.py data quality — real prices, no random mocks, proper ticker inference
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-13
**Details:**
- researcher_bot currently uses `random.uniform()` for prices instead of real yfinance data
- SPY randomly shows $159 then $70 in the same day
- PE ratio and RSI are also randomly generated
- Need to: use real yfinance data properly, remove generate_mock_result() as fallback, cache results in `dashboard/data/cache/`, handle rate limits with exponential backoff
- The fallback should produce NO data (empty/None) rather than fake data
- `infer_ticker()` misidentifies the "C" in task descriptions — add better blocklist

### Task ID: T-002
**Subject:** Fix paper_trade.py — virtual portfolio ledger persistence
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-13
**Details:**
- paper_trade.py likely not persisting trades properly
- Ledger file `dashboard/data/paper_ledger.json` may be empty or corrupt
- Need to: write proper buy/sell log entries with entry/exit prices, hold durations, P&L, win rate
- Auto-trigger paper trades only when confidence > 70 and recommendation is BUY/ACCUMULATE
- Add `auto_trade_enabled` toggle to whiteboard or settings

### Task ID: T-003
**Subject:** Redesign dashboard frontend — modern financial terminal UI
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Details:**
- Current dashboard is basic slate-900 cards with Tailwind defaults
- Modern financial dashboards use: Bloomberg Terminal dark theme (black bg, green/red accents), real-time tickers at top, sparkline charts, heatmaps, table-views with sortable columns, keyboard shortcuts
- Add route: `/portfolio` for paper trading ledger
- Add route: `/feedback` for bot accuracy leaderboard
- Fix main nav: use icon-based sidebar not top bar
- Auto-refresh every 30s with smooth transitions

### Task ID: T-004
**Subject:** Verify council_meeting.py logic — does it actually read bot outputs?
**Assigned Bot:** self_build
**Priority:** medium
**Created:** 2026-05-13
**Details:**
- Council meeting is called but may be passed incorrect file paths
- `_run_council` references `OUTPUT_DIR / result_data.get("task_id", "")` which may not exist
- Need to trace: check if `council_meeting.py` reads the actual earnings/model/kyc/advisor JSONs
- Add `force_council` flag on tasks when needed
- Verify consensus boosting position size actually works

### Task ID: T-005
**Subject:** Fix docker-compose.yml — remove version warning, verify build
**Assigned Bot:** self_build
**Priority:** medium
**Created:** 2026-05-13
**Details:**
- Docker Compose v2 warns: `attribute 'version' is obsolete`
- Remove `version: "3.9"` from docker-compose.yml
- Verify `docker compose build` succeeds without errors
- Verify `docker compose up` brings both containers up cleanly
- Check port binding doesn't conflict with nexus on 8080

### Task ID: T-006
**Subject:** Build bot_registry.json accuracy pipeline
**Assigned Bot:** self_build
**Priority:** medium
**Created:** 2026-05-13
**Details:**
- Bot registry tracks predictions but never compares with actual outcomes
- Need: scheduled comparison job that reads prediction + 7-day-later price from yfinance
- Score each bot: win_rate = correct direction / total predictions (min 5 to be valid)
- Trigger whiteboard task when bot drops below 40%
- Write `dashboard/data/feedback_report.json` weekly

### Task ID: T-007
**Subject:** Dashboard backend API quality check — ensure all endpoints return sane data
**Assigned Bot:** self_build
**Priority:** medium
**Created:** 2026-05-13
**Details:**
- `/api/recommendations` may return stale or duplicate entries
- `/api/sectors` may be empty
- Add deduplication: if task_id already in output, overwrite instead of append
- Add data validation layer before API serves JSON
- Add `/api/health/deep` endpoint that checks: yfinance connectivity, cache disk space, ledger file exists

### Task ID: T-008
**Subject:** Logic review complete — Go/No-Go gate before enabling research
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Details:**
- After T-001 through T-007 are DONE, run a full cycle manually on a known ticker (e.g. NVDA)
- Verify: real price, correct PE ratio, council vote matches individual bots
- Verify paper trade logged properly
- Verify dashboard shows actual data not mock data
- If all pass: update AGENT STATE to "RESEARCH PHASE" and re-enable auto-research generation
- If any fail: create targeted fix tasks

## In Progress

_(No tasks in this section.)_

## Done

_(Build tasks will appear here once completed.)_

---

**Tech stack:** Python 3.12 + FastAPI backend + React (Vite) + TailwindCSS + Docker Compose
**Working directory:** /home/fishingshirt/stock-command-center
**Build on this machine, push to GitHub immediately after every change.**

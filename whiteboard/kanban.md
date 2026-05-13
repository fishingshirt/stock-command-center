# Stock Command Center — Whiteboard

This is the single source of truth for all research and build tasks. Do not edit outside the three sections below.

---

## To Do

### Task ID: 20260513-021
**Subject:** Auto: Tune VALUE strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Details:**
- Strategy: VALUE
- Win rate: 0.0% over 15 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-022
**Subject:** Auto: Tune MOMENTUM strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Details:**
- Strategy: MOMENTUM
- Win rate: 0.0% over 19 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-023
**Subject:** Auto: Tune GROWTH strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Details:**
- Strategy: GROWTH
- Win rate: 0.0% over 85 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

## In Progress

_(No tasks in this section.)_

## Done

### Task ID: T-001
**Subject:** Fix researcher_bot.py data quality — real prices, no random mocks, proper ticker inference
**Assigned Bot:** self_build
**Priority:** critical
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:08.510601+00:00
**Completed At:** 2026-05-13T13:00:09.811772+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - researcher_bot currently uses `random.uniform()` for prices instead of real yfinance data
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
**Started At:** 2026-05-13T13:00:11.117668+00:00
**Completed At:** 2026-05-13T13:00:12.533714+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - paper_trade.py likely not persisting trades properly
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
**Started At:** 2026-05-13T13:00:13.989198+00:00
**Completed At:** 2026-05-13T13:00:15.241226+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Current dashboard is basic slate-900 cards with Tailwind defaults
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
**Started At:** 2026-05-13T13:00:16.448354+00:00
**Completed At:** 2026-05-13T13:00:17.811013+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** Passed: 3/3 — Failed: []
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
**Started At:** 2026-05-13T13:00:19.209471+00:00
**Completed At:** 2026-05-13T13:00:20.695350+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** time="2026-05-13T13:00:20Z" level=warning msg="/home/fishingshirt/stock-command-center/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"
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
**Started At:** 2026-05-13T13:00:21.916404+00:00
**Completed At:** 2026-05-13T13:00:23.140736+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Bot registry tracks predictions but never compares with actual outcomes
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
**Started At:** 2026-05-13T13:00:24.430581+00:00
**Completed At:** 2026-05-13T13:00:25.709480+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** All Python files compile OK
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
**Started At:** 2026-05-13T13:00:26.992506+00:00
**Completed At:** 2026-05-13T13:00:28.343793+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - After T-001 through T-007 are DONE, run a full cycle manually on a known ticker (e.g. NVDA)
**Details:**
- After T-001 through T-007 are DONE, run a full cycle manually on a known ticker (e.g. NVDA)
- Verify: real price, correct PE ratio, council vote matches individual bots
- Verify paper trade logged properly
- Verify dashboard shows actual data not mock data
- If all pass: update AGENT STATE to "RESEARCH PHASE" and re-enable auto-research generation
- If any fail: create targeted fix tasks

### Task ID: 20260513-001
**Subject:** Auto: Tune VALUE strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:29.453993+00:00
**Completed At:** 2026-05-13T13:00:30.600638+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: VALUE
**Details:**
- Strategy: VALUE
- Win rate: 0.0% over 15 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-002
**Subject:** Auto: Tune MOMENTUM strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:32.005965+00:00
**Completed At:** 2026-05-13T13:00:33.282258+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: MOMENTUM
**Details:**
- Strategy: MOMENTUM
- Win rate: 0.0% over 18 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-003
**Subject:** Auto: Tune GROWTH strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:34.576623+00:00
**Completed At:** 2026-05-13T13:00:36.026434+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: GROWTH
**Details:**
- Strategy: GROWTH
- Win rate: 0.0% over 82 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-004
**Subject:** Auto: Tune VALUE strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:40.540477+00:00
**Completed At:** 2026-05-13T13:00:41.871084+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: VALUE
**Details:**
- Strategy: VALUE
- Win rate: 0.0% over 15 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-005
**Subject:** Auto: Tune MOMENTUM strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:43.069176+00:00
**Completed At:** 2026-05-13T13:00:44.408975+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: MOMENTUM
**Details:**
- Strategy: MOMENTUM
- Win rate: 0.0% over 18 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-006
**Subject:** Auto: Tune GROWTH strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:45.734707+00:00
**Completed At:** 2026-05-13T13:00:47.195391+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: GROWTH
**Details:**
- Strategy: GROWTH
- Win rate: 0.0% over 82 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-007
**Subject:** Auto: Top crypto momentum scan (BTC, ETH, SOL)
**Assigned Bot:** researcher_bot
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:48.391547+00:00
**Completed At:** 2026-05-13T13:00:50.094369+00:00
**Result:** dashboard/data/output/20260513-007.json
**Summary:** ACCUMULATE (60%) — Strategy: GROWTH. Council: HOLD (83.3% STRONG CONSENSUS) [+25% size]
**Details:**
- Pull Coingecko data
- Volume and price change analysis
- Momentum score and recommendation

### Task ID: 20260513-008
**Subject:** Auto: S&P 500 top movers sentiment scan
**Assigned Bot:** researcher_bot
**Priority:** medium
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:51.625705+00:00
**Completed At:** 2026-05-13T13:00:53.181539+00:00
**Result:** dashboard/data/output/20260513-008.json
**Summary:** ACCUMULATE (68%) — Strategy: GROWTH. Council: HOLD (83.3% STRONG CONSENSUS) [+25% size]
**Details:**
- Identify top 5 daily movers
- Fundamentals check
- News sentiment
- Investment recommendation

### Task ID: 20260513-009
**Subject:** Auto: Sector rotation — tech vs energy vs biotech
**Assigned Bot:** researcher_bot
**Priority:** low
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:00:54.639682+00:00
**Completed At:** 2026-05-13T13:00:55.905395+00:00
**Result:** dashboard/data/output/20260513-009.json
**Summary:** ACCUMULATE (51%) — Strategy: GROWTH. Council: HOLD (83.3% STRONG CONSENSUS) [+25% size]
**Details:**
- Compare sector ETF performance
- Relative strength analysis
- Rotation signal detection

### Task ID: 20260513-010
**Subject:** Auto: Tune VALUE strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:15:07.259138+00:00
**Completed At:** 2026-05-13T13:15:08.385652+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: VALUE
**Details:**
- Strategy: VALUE
- Win rate: 0.0% over 15 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-011
**Subject:** Auto: Tune MOMENTUM strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:15:09.801270+00:00
**Completed At:** 2026-05-13T13:15:11.054470+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: MOMENTUM
**Details:**
- Strategy: MOMENTUM
- Win rate: 0.0% over 18 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-012
**Subject:** Auto: Tune GROWTH strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:15:12.469505+00:00
**Completed At:** 2026-05-13T13:15:13.819140+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: GROWTH
**Details:**
- Strategy: GROWTH
- Win rate: 0.0% over 85 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-013
**Subject:** Auto: S&P 500 top movers sentiment scan
**Assigned Bot:** researcher_bot
**Priority:** medium
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:16:11.047907+00:00
**Completed At:** 2026-05-13T13:16:12.432674+00:00
**Result:** dashboard/data/output/20260513-013.json
**Summary:** ACCUMULATE (85%) — Strategy: MOMENTUM. Council: HOLD (83.3% STRONG CONSENSUS) [+25% size]
**Details:**
- Identify top 5 daily movers
- Fundamentals check
- News sentiment
- Investment recommendation

### Task ID: 20260513-014
**Subject:** Auto: Tune VALUE strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:16:13.903707+00:00
**Completed At:** 2026-05-13T13:16:15.065820+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: VALUE
**Details:**
- Strategy: VALUE
- Win rate: 0.0% over 15 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-015
**Subject:** Auto: Tune MOMENTUM strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:16:16.361069+00:00
**Completed At:** 2026-05-13T13:16:17.613928+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: MOMENTUM
**Details:**
- Strategy: MOMENTUM
- Win rate: 0.0% over 18 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-016
**Subject:** Auto: Tune GROWTH strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:16:18.868473+00:00
**Completed At:** 2026-05-13T13:16:20.198795+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: GROWTH
**Details:**
- Strategy: GROWTH
- Win rate: 0.0% over 85 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-017
**Subject:** Auto: Tune VALUE strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:30:07.546350+00:00
**Completed At:** 2026-05-13T13:30:09.012725+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: VALUE
**Details:**
- Strategy: VALUE
- Win rate: 0.0% over 15 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-018
**Subject:** Auto: Tune MOMENTUM strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:30:10.261360+00:00
**Completed At:** 2026-05-13T13:30:11.472700+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: MOMENTUM
**Details:**
- Strategy: MOMENTUM
- Win rate: 0.0% over 19 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-019
**Subject:** Auto: Tune GROWTH strategy parameters
**Assigned Bot:** self_build
**Priority:** high
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:30:12.776922+00:00
**Completed At:** 2026-05-13T13:30:14.648942+00:00
**Result:** /home/fishingshirt/stock-command-center/logs/self_build.log
**Summary:** No actionable build steps for: - Strategy: GROWTH
**Details:**
- Strategy: GROWTH
- Win rate: 0.0% over 85 trades
- Target: improve to >= 45.0%
- Suggestion: adjust entry/exit thresholds or combine with another strategy
- Created via feedback_loop auto-improve

### Task ID: 20260513-020
**Subject:** Auto: S&P 500 top movers sentiment scan
**Assigned Bot:** researcher_bot
**Priority:** medium
**Created:** 2026-05-13
**Started At:** 2026-05-13T13:30:27.019608+00:00
**Completed At:** 2026-05-13T13:30:28.430836+00:00
**Result:** dashboard/data/output/20260513-020.json
**Summary:** ACCUMULATE (72%) — Strategy: VALUE. Council: HOLD (83.3% STRONG CONSENSUS) [+25% size]
**Details:**
- Identify top 5 daily movers
- Fundamentals check
- News sentiment
- Investment recommendation

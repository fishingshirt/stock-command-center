# SCC Kanban Multi-Agent Architecture — Blueprint

> **Status:** DRAFT — awaiting review  
> **Date:** 2026-05-21  
> **Author:** Hermes Agent (Jay's SCC)  
> **Goal:** Convert SCC from monolithic Python orchestrator to autonomous Kanban-driven multi-agent ecosystem

---

## 1. Current State Audit

### What exists (the v3 system)

```
cron (every 15 min)
  └── run_cycle.py → main_orchestrator.py
        ├── git pull
        ├── load whiteboard/kanban.md (13K+ line markdown file)
        ├── pick ≤5 "To Do" tasks
        ├── for each task (SEQUENTIAL):
        │     ├── subprocess: researcher_bot.py (yfinance → signals)
        │     ├── subprocess: financial_model.py (DCF valuation)
        │     ├── subprocess: earnings_analyzer.py (catalyst scoring)
        │     ├── subprocess: advisor_reasoning.py (thesis synthesis)
        │     ├── auto_trade_from_result() (paper buy/sell with live prices)
        │     └── move task "To Do" → "Done" on whiteboard
        ├── auto-generate 5 new watchlist tasks
        └── git push
```

**Python bots directory** (`bots/`):
| File | Role | Status |
|------|------|--------|
| `main_orchestrator.py` | Monolithic loop runner | Active |
| `researcher_bot.py` | yfinance, RSI, momentum, sentiment → BUY/HOLD/SELL | Active |
| `financial_model.py` | DCF blended target, margin of safety | Active |
| `earnings_analyzer.py` | Catalyst scoring, EPS trend | Active |
| `advisor_reasoning.py` | Strategy rationale synthesis | Active |
| `portfolio_constructor.py` | Kelly criterion, position sizing | Not integrated |
| `paper_trade.py` | $100K paper trading, rotation, sanity checks | Active |
| `strategy_tracker.py` | Strategy performance ledger | Partially hooked |
| `self_build.py` | Docker rebuild, strategy tuning, test/verify | Active |
| `kyc_screen.py` | Compliance/risk check | Registered, unused |
| `pitchbook_generator.py` | Investment memo generation | Registered, unused |
| `bot_registry.py` | Accuracy tracking per bot | Active |

**Dashboard**: FastAPI backend (`:8000`) + React frontend (`:8081`) in Docker.  
**Watchlist**: 47 tickers (ETFs, mega-cap tech, banks, energy, healthcare, consumer, crypto).  
**Whiteboard**: 13K+ line `kanban.md` — mostly historical Done tasks. 7 tasks in To Do (all ETF analysis).

### What works well
- Real financial data via yfinance (with chart API fallback for rate limits)
- Coingecko for crypto, Yahoo RSS for news sentiment
- 8-category signal scoring engine (momentum, RSI, SMA, P/E ratios, revenue/earnings growth, 52-week position, volume, sentiment)
- Paper trading with live prices, sanity checks (±25% reject), conviction-scaled sizing, rotation
- Strategy auto-tuning based on win rates
- Docker health checks pass

### Core limitations (why this needs a rebuild)
1. **Sequential**: All bots run one-at-a-time in a single Python process
2. **No specialist memory**: Each bot is stateless — no learning across cycles
3. **No parallelism**: 5 ticker analyses can't fan out simultaneously
4. **Markdown bottleneck**: 13K+ line whiteboard — increasingly slow to parse
5. **No cross-agent communication**: Bots can't read each other's findings mid-cycle
6. **No true autonomy**: The system runs what it's told; it doesn't decide what to research, what to build, or what to fix
7. **Cron-based, not event-driven**: 15-min polling means market events are missed

---

## 2. Target Architecture

```
                    ┌──────────────────────────────────┐
                    │   SCC Cron Trigger (Hermes)       │
                    │   Every 15 min during market      │
                    │   hours only                      │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │   HEAD MANAGER (orchestrator)     │
                    │   Profile: scc-head-manager       │
                    │   Model: deepseek-v4-pro          │
                    │   Tools: web, terminal, file,     │
                    │          cronjob, kanban_*        │
                    │   ┌──────────────────────────┐    │
                    │   │ 1. Check market hours     │    │
                    │   │ 2. Scan whiteboard backlog│    │
                    │   │ 3. Decompose into cards   │    │
                    │   │ 4. Create parallel lanes  │    │
                    │   │ 5. Review outcomes        │    │
                    │   │ 6. Spawn self-improvement │    │
                    │   │ 7. Generate daily report  │    │
                    │   └──────────────────────────┘    │
                    └──────────────┬───────────────────┘
                                   │ kanban_create()
                                   ▼
    ┌──────────────────── HERMES KANBAN BOARD ────────────────────┐
    │                                                               │
    │  RESEARCH LANE (parallel)                                     │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐  │
    │  │ NVDA    │ │ AAPL    │ │ TSLA    │ │ BTC     │ │ SPY   │  │
    │  │research │ │research │ │research │ │research │ │research│  │
    │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬───┘  │
    │       │           │           │           │          │       │
    │  ┌────▼───────────▼───────────▼───────────▼──────────▼───┐  │
    │  │              ANALYSIS LANE (depends on research)       │  │
    │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │  │
    │  │  │ financial   │ │ earnings    │ │ advisor         │  │  │
    │  │  │ model       │ │ analysis    │ │ reasoning       │  │  │
    │  │  └──────┬──────┘ └──────┬──────┘ └───────┬─────────┘  │  │
    │  │         └───────────────┼────────────────┘            │  │
    │  │                         ▼                              │  │
    │  │              ┌─────────────────┐                       │  │
    │  │              │ paper trade     │                       │  │
    │  │              │ (if BUY/ACCUM)  │                       │  │
    │  │              └─────────────────┘                       │  │
    │  └───────────────────────────────────────────────────────┘  │
    │                                                               │
    │  REVIEW LANE (post-trade, periodic)                           │
    │  ┌──────────────────┐  ┌──────────────────┐                  │
    │  │ strategy review  │  │ self-build/      │                  │
    │  │ (evaluate closed │──│ tune params      │                  │
    │  │  trades, stats)  │  │ (apply changes)  │                  │
    │  └──────────────────┘  └──────────────────┘                  │
    └───────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │   DELIVERABLES                    │
                    │   • Discord #daily-update report  │
                    │   • Dashboard API (port 8000)     │
                    │   • Git-persisted results         │
                    └──────────────────────────────────┘
```

### Key design principles
- **Decompose, don't execute**: The Head Manager creates cards, doesn't do the research itself
- **Parallel by default**: Research tasks for different tickers fan out simultaneously
- **Dependency gates**: Analysis cards wait until research parents complete
- **Structured handoffs**: Every `kanban_complete()` includes machine-parseable metadata
- **Self-improvement**: Strategy review feeds into self-build, closing the feedback loop
- **Memory per specialist**: Each profile accumulates knowledge — a researcher learns which data sources fail, a trader learns which signals are noise

---

## 3. Profile Definitions

> All profiles use `deepseek-v4-pro` via `ollama-cloud` (the current default provider).  
> Created with `hermes profile create <name> --model deepseek-v4-pro`.

### 3.1 `scc-head-manager` (orchestrator)

**Role**: Decompose work, create Kanban cards, review outcomes, generate daily report.

**Toolsets**: `web`, `terminal`, `file`, `cronjob`, `search`, `session_search`

**System prompt additions**:
```
You are the Head Manager of the Stock Command Center — a Wall Street-style 
autonomous trading research desk. You do NOT execute research yourself.

Your job:
1. Check US market hours (9:30 AM–4:00 PM ET, Mon–Fri)
2. Read the whiteboard backlog
3. Create RESEARCH cards (parallel fan-out) for watchlist tickers
4. Create ANALYSIS cards (with parent dependencies on research)
5. Create TRADE cards (with parent dependencies on analysis)
6. After trades close, create STRATEGY REVIEW cards
7. Generate daily summary → Discord #daily-update

Anti-temptation rules:
- NEVER run researcher_bot.py yourself — create a card for scc-researcher
- NEVER run paper_trade.py yourself — create a card for scc-trader
- Split independent work into separate cards with no parent links
- Only link cards when one truly depends on another's output
- Use the Kanban tools (kanban_create, kanban_show) — not subprocess

Market hours check:
```python
import pytz, datetime
et = pytz.timezone('US/Eastern')
now = datetime.datetime.now(et)
is_market_open = (
    now.weekday() < 5 and
    datetime.time(9, 30) <= now.time() <= datetime.time(16, 0)
)
```
Only create trade cards when market is open.

Report to Discord:
Use send_message(target="discord:#daily-update", message=report) for daily summaries.
```

**Skills to load**: `kanban-orchestrator`

### 3.2 `scc-researcher` (leaf worker)

**Role**: Fetch real market data for a single ticker, compute signals, produce recommendation.

**Toolsets**: `terminal`, `file`, `web`

**System prompt additions**:
```
You are a quantitative research analyst for the Stock Command Center.
Given a ticker, you run the research pipeline:
  python bots/researcher_bot.py --task-id $TASK_ID --subject "$SUBJECT" --output $OUTPUT_PATH

Rules:
- Always use the real researcher_bot.py — never fabricate prices or signals
- Read the task body for the ticker and subject
- After running, read the output JSON to verify it has real data
- If the bot returns NO_DATA, complete the card with status=no_data (not failed)
- Include key metrics in your kanban_complete summary: ticker, price, recommendation, confidence, strategy
- Use structured metadata: {"ticker": "...", "price": ..., "recommendation": "...", "confidence": ..., "strategy": "...", "output_file": "..."}
```

### 3.3 `scc-analyst` (leaf worker)

**Role**: Run financial model + earnings analysis + advisor reasoning for a ticker.

**Toolsets**: `terminal`, `file`

**System prompt additions**:
```
You are a financial analyst for the Stock Command Center.
Given a completed research task (read its output JSON), run:

1. python bots/financial_model.py --ticker $TICKER --output $MODEL_PATH
2. python bots/earnings_analyzer.py --ticker $TICKER --output $EARNINGS_PATH
3. python bots/advisor_reasoning.py --research $RESEARCH_PATH --model $MODEL_PATH --earnings $EARNINGS_PATH --output $ADVISOR_PATH

Then synthesize findings into your kanban_complete summary.
Include: valuation verdict, margin of safety, catalyst score, blended thesis.
```

### 3.4 `scc-trader` (leaf worker)

**Role**: Execute paper trades based on completed research + analysis.

**Toolsets**: `terminal`, `file`

**System prompt additions**:
```
You are a paper trader for the Stock Command Center.
Read the research JSON from the parent task. Call:

  python bots/paper_trade.py

But first check the recommendation, confidence, and market hours.
Only execute if:
- recommendation in (BUY, ACCUMULATE) and confidence >= threshold (60%)
- OR recommendation in (SELL, REDUCE) and position is open

Use the paper_trade.py module directly (import, don't subprocess):
```python
from bots.paper_trade import auto_trade_from_result, get_stats
import json

with open(research_path) as f:
    result = json.load(f)
    
trade = auto_trade_from_result(result)
stats = get_stats()
```

Report: what was traded, portfolio value, open positions count.
```

### 3.5 `scc-builder` (leaf worker)

**Role**: Self-improvement — strategy tuning, Docker rebuilds, bug fixes, git commits.

**Toolsets**: `terminal`, `file`, `web`

**System prompt additions**:
```
You are the self-build engineer for the Stock Command Center.
You can:
1. Run strategy tuning: python bots/self_build.py
2. Rebuild Docker: cd ~/stock-command-center && sudo docker compose up -d --build
3. Run verification: curl health endpoints
4. Fix bugs in bots/*.py
5. Git commit and push changes

Always verify after changes:
- curl -s http://localhost:8000/health
- curl -s http://localhost:8081/ | head -5
```

### 3.6 `scc-reviewer` (leaf worker)

**Role**: Evaluate closed trades, compute strategy stats, recommend adjustments.

**Toolsets**: `terminal`, `file`

**System prompt additions**:
```
You are the strategy reviewer for the Stock Command Center.
Read the strategy ledger and paper trading history:

```python
from bots.strategy_tracker import get_leaderboard
from bots.paper_trade import get_stats

leaderboard = get_leaderboard()
stats = get_stats()
```

Produce a review with:
- Per-strategy win rates and avg returns
- Which strategies need threshold adjustments
- Recommendations for watchlist rotation (add/remove tickers)
- Flag any data-quality issues (stale prices, repeated failures)
```

---

## 4. Kanban Lane Design

### Card types and flows

```
┌─────────────────────────────────────────────────────────────────┐
│  LANE 1: RESEARCH (parallel, no parents)                        │
│                                                                  │
│  T1: "NVDA analysis" → scc-researcher                           │
│  T2: "AAPL analysis" → scc-researcher  ← all run simultaneously │
│  T3: "TSLA analysis" → scc-researcher                           │
│  T4: "SPY analysis"  → scc-researcher                           │
│  T5: "BTC-USD analysis" → scc-researcher                        │
│                                                                  │
│  Template body:                                                  │
│  """                                                            │
│  Ticker: {TICKER}                                               │
│  Subject: {TICKER} analysis                                     │
│  Task: Run researcher_bot.py for {TICKER}.                      │
│  Output: dashboard/data/output/{TASK_ID}.json                   │
│  """                                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ parents=[T1, T2, T3, T4, T5]
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANE 2: ANALYSIS (depends on ALL research)                     │
│                                                                  │
│  T6: "Financial models batch" → scc-analyst                     │
│       Reads all research outputs, runs financial_model.py       │
│       for each ticker with BUY/ACCUMULATE recommendation        │
│                                                                  │
│  T7: "Earnings analysis batch" → scc-analyst                    │
│       Same — runs earnings_analyzer.py for each ticker          │
│                                                                  │
│  T8: "Advisor reasoning batch" → scc-analyst                    │
│       Runs advisor_reasoning.py for each ticker                 │
│                                                                  │
│  These could also be per-ticker with individual parent links.   │
│  Batch is more efficient when 5 tickers are analyzed at once.   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ parents=[T6, T7, T8]
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANE 3: TRADE (depends on analysis)                            │
│                                                                  │
│  T9: "Execute paper trades" → scc-trader                        │
│       Reads all enriched research outputs.                      │
│       Calls auto_trade_from_result() for each.                  │
│       Only executes during market hours.                        │
│       Reports: trades executed, portfolio value, positions.     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANE 4: REVIEW (periodic, e.g. daily at 4:30 PM ET)           │
│                                                                  │
│  T10: "Strategy performance review" → scc-reviewer              │
│        Computes per-strategy stats, identifies underperformers  │
│                                                                  │
│  T11: "Tune strategy parameters" → scc-builder                  │
│        parents=[T10]                                            │
│        Applies threshold adjustments from review                │
│                                                                  │
│  T12: "Daily report to Discord" → scc-head-manager              │
│        parents=[T9, T10]                                        │
│        Generates markdown summary → Discord #daily-update       │
└─────────────────────────────────────────────────────────────────┘
```

### Card template (what head manager creates)

```python
# Research card
kanban_create(
    title="NVDA analysis",
    assignee="scc-researcher",
    body="""Ticker: NVDA
Subject: NVDA analysis
Task: Run researcher_bot.py for NVDA with real yfinance data.
Output path: dashboard/data/output/{task_id}.json
Expected: BUY/SELL/HOLD recommendation with confidence and signal breakdown.
On failure: mark as NO_DATA in summary, do not retry more than twice.""",
    priority="high",
    tags=["research", "NVDA", "tech"],
)

# Trade card (only created when market is open)
kanban_create(
    title="Execute paper trades for cycle {cycle_id}",
    assignee="scc-trader",
    body="""Read all research outputs from parents. Execute paper trades for any BUY/ACCUMULATE 
above 60% confidence. Sell any SELL/REDUCE positions. Report portfolio state after execution.""",
    parents=[analysis_task_id],
    priority="high",
    tags=["trade", "paper"],
)
```

---

## 5. Worker Skills

Each profile needs a skill file so workers know exactly which files and commands to use.

### 5.1 `scc-researcher` skill

```yaml
name: scc-researcher
description: Run the SCC researcher_bot.py for a single ticker — yfinance data, signals, recommendation.
```

Steps:
1. Read `kanban_show()` to get ticker from task body
2. Run: `python ~/stock-command-center/bots/researcher_bot.py --task-id $TASK_ID --subject "$SUBJECT" --output ~/stock-command-center/dashboard/data/output/$TASK_ID.json`
3. Read output JSON, verify it has `recommendation` and `current_price`
4. If `recommendation == "NO_DATA"`, complete with `status: no_data`
5. Otherwise complete with structured metadata

### 5.2 `scc-analyst` skill

```yaml
name: scc-analyst
description: Run financial model, earnings analysis, and advisor reasoning for tickers with completed research.
```

Steps:
1. Read parent research tasks to get tickers and output paths
2. For each ticker with BUY/ACCUMULATE:
   a. `python ~/stock-command-center/bots/financial_model.py --ticker TICKER --output ~/stock-command-center/dashboard/data/models/TICKER.json`
   b. `python ~/stock-command-center/bots/earnings_analyzer.py --ticker TICKER --output ~/stock-command-center/dashboard/data/earnings/TICKER.json`
   c. `python ~/stock-command-center/bots/advisor_reasoning.py --research RESEARCH_PATH --model MODEL_PATH --earnings EARNINGS_PATH --output ~/stock-command-center/dashboard/data/advisor_notes/TICKER.json`
3. Complete with summary of all tickers analyzed

### 5.3 `scc-trader` skill

```yaml
name: scc-trader
description: Execute paper trades from completed research + analysis.
```

Steps:
1. Read parent analysis task to find enriched research JSON files
2. For each: `from bots.paper_trade import auto_trade_from_result; result = auto_trade_from_result(data)`
3. Run `get_stats()` for portfolio summary
4. Complete with trades executed, portfolio value, open positions

### 5.4 `scc-reviewer` skill

```yaml
name: scc-reviewer
description: Review closed trades, compute strategy stats, recommend adjustments.
```

Steps:
1. `from bots.paper_trade import get_stats; stats = get_stats()`
2. `from bots.strategy_tracker import get_leaderboard; lb = get_leaderboard()`
3. Identify strategies with win_rate < 40% or > 65%
4. Recommend threshold adjustments
5. Complete with structured review

### 5.5 `scc-builder` skill

```yaml
name: scc-builder
description: Apply strategy tuning, rebuild Docker, fix bugs, commit changes.
```

Steps:
1. If strategy tuning: run self_build.py, verify config.json updated
2. If Docker rebuild: `cd ~/stock-command-center && sudo docker compose up -d --build`
3. Verify: `curl -s localhost:8000/health` and `curl -s localhost:8081/`
4. Git add, commit, push
5. Complete with build log summary

---

## 6. Head Manager Orchestration Logic

The Head Manager runs as a cron job (replacing `run_cycle.py`). Its logic:

```
┌─────────────────────────────────────────┐
│  HEAD MANAGER CYCLE (every 15 min)      │
├─────────────────────────────────────────┤
│                                          │
│  1. MARKET CHECK                         │
│     if market closed:                    │
│       → skip trade cards                 │
│       → still create research cards      │
│       → create review cards if EOD       │
│                                          │
│  2. SCAN BACKLOG                         │
│     kanban_list(status="ready")          │
│     if count < 3: generate new           │
│                                          │
│  3. GENERATE RESEARCH CARDS              │
│     • Pick 5 tickers from rotating       │
│       watchlist (not recently done)      │
│     • Create parallel research cards     │
│     • Capture returned task_ids          │
│                                          │
│  4. GENERATE ANALYSIS CARDS              │
│     • Create with parents=research_ids   │
│     • Gate ensures analysis waits        │
│       for all research to complete       │
│                                          │
│  5. GENERATE TRADE CARD (market open)    │
│     • parents=analysis_ids               │
│                                          │
│  6. CHECK COMPLETED CYCLES               │
│     • Look for cycles where trade card   │
│       is done                            │
│     • If EOD (after 4 PM ET):            │
│       → create strategy review card      │
│       → create daily report card         │
│                                          │
│  7. SELF-IMPROVEMENT TRIGGERS            │
│     • If errors > threshold in logs:     │
│       → create debug/fix card            │
│     • If strategy win rates shift:       │
│       → create tune card                 │
│     • Weekly: full system health audit   │
│                                          │
└─────────────────────────────────────────┘
```

### Watchlist rotation

The Head Manager maintains a rotating watchlist (same 47 tickers). It:
- Tracks recently analyzed tickers (last 24h via Kanban completed cards)
- Prioritizes tickers not analyzed recently
- Includes 2-3 ETFs, 2-3 stocks, 0-1 crypto per cycle
- Rotates sectors: tech → banks → energy → healthcare → consumer → repeat

---

## 7. Self-Improvement Loop

```
                    ┌──────────────────────┐
                    │  Paper trade closes   │
                    │  (position sold)      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  scc-reviewer        │
                    │  • Reads ledger      │
                    │  • Computes per-     │
                    │    strategy stats    │
                    │  • Flags under-      │
                    │    performers        │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  scc-builder         │
                    │  • Lowers confidence │
                    │    thresholds for    │
                    │    losing strategies │
                    │  • Raises for winners│
                    │  • Adjusts rotation  │
                    │  • Commits changes   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Next cycle picks up │
                    │  tuned parameters    │
                    │  → better trades     │
                    └──────────────────────┘
```

Feedback metrics tracked:
- Per-strategy win rate (paper trading)
- Per-strategy average return
- Per-bot prediction accuracy (bot_registry)
- Signal category effectiveness (which signals correlate with wins)
- Research success rate (NO_DATA vs real data)

---

## 8. Migration Plan

### Phase 1: Profile Setup (Day 1)
- [ ] Create 6 Hermes profiles: `scc-head-manager`, `scc-researcher`, `scc-analyst`, `scc-trader`, `scc-reviewer`, `scc-builder`
- [ ] Write system prompts for each
- [ ] Create worker skills (`scc-researcher`, `scc-analyst`, `scc-trader`, `scc-reviewer`, `scc-builder`)
- [ ] Verify each profile can run its bot: manual test with one ticker

### Phase 2: Head Manager Cron (Day 1-2)
- [ ] Write Head Manager cron prompt
- [ ] Test: create research cards → verify workers pick them up
- [ ] Test: analysis gates → verify dependency chain
- [ ] Test: trade card → verify paper trade executes

### Phase 3: Parallel Cutover (Day 2)
- [ ] Replace `scc-orchestrator` cron with Head Manager cron
- [ ] Pause old cron, run new in parallel for 1 day
- [ ] Compare outputs: same tickers, same recommendations?
- [ ] Verify paper trading produces identical results

### Phase 4: Self-Improvement (Day 2-3)
- [ ] Wire strategy review card creation
- [ ] Wire self-build → tune → commit flow
- [ ] Test: close a trade, verify review fires, verify parameters update

### Phase 5: Dashboard + Reports (Day 3)
- [ ] Update dashboard API to read Kanban board state
- [ ] Wire daily Discord report
- [ ] Add Kanban board panel to frontend

### Phase 6: Decommission (Day 4+)
- [ ] Remove old `main_orchestrator.py` cron
- [ ] Archive markdown whiteboard (keep for history)
- [ ] Monitor for 1 week, tune as needed

---

## 9. Cron Job Design

### Current cron (to be replaced)
```
Job: scc-orchestrator
Schedule: every 15 min
Command: python bots/run_cycle.py
```

### New cron (Kanban-based)
```
Job: scc-head-manager-cycle
Schedule: every 15 min
Model: deepseek-v4-pro
Skills: [kanban-orchestrator, scc-researcher, scc-analyst, scc-trader]
Prompt: |
  You are the SCC Head Manager. This is a cron-fired cycle.
  
  1. Check if US market is open (9:30 AM–4:00 PM ET, Mon–Fri).
  2. Check the Kanban board backlog: any ready research cards? If < 3, generate new ones.
  3. Generate 5 research cards for tickers from the rotating watchlist. Use kanban_create with assignee="scc-researcher".
  4. Capture the task IDs. Create 1 analysis batch card with parents=those IDs, assignee="scc-analyst".
  5. If market is open: create 1 trade card with parent=analysis_card, assignee="scc-trader".
  6. If after 4 PM ET: create strategy review card, assignee="scc-reviewer".
  7. If review card completes: create self-build card with parent=review, assignee="scc-builder".
  8. If review complete: generate daily report → send_message to discord:#daily-update.
  
  Do NOT execute research yourself. Create cards and let the dispatcher handle it.
Deliver: local (no delivery — workers handle output)
```

---

## 10. Dashboard Updates

### New API endpoints needed
```python
GET /api/kanban/board        # Kanban board state (ready/in_progress/done counts)
GET /api/kanban/recent        # Last 20 completed cards with summaries
GET /api/agents/status        # Per-profile: last active, tasks completed, accuracy
GET /api/strategies/review    # Latest strategy review output
```

### Frontend panels to add
- **Kanban Board** panel: columns for Ready/In Progress/Done with card cards
- **Agent Status** panel: which profiles are active, last task, success rate
- **Self-Improvement Log**: recent tuning changes, what was adjusted and why

### Dashboard wireframe
```
┌──────────────────────────────────────────────────────────────┐
│  STOCK COMMAND CENTER                      [Market: CLOSED]  │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  PORTFOLIO  │  RESEARCH   │  KANBAN     │  AGENTS           │
│  $100,000   │  QUEUE      │  BOARD      │                   │
│  0 pos      │  NVDA ⏳     │  Ready: 5   │  researcher: 🟢   │
│  0 P&L      │  AAPL ⏳     │  Active: 2  │  analyst: 🟢     │
│             │  TSLA ⏳     │  Done: 142  │  trader: 🟡      │
│             │             │             │  reviewer: ⚪     │
├─────────────┴─────────────┴─────────────┴───────────────────┤
│  LATEST RECOMMENDATIONS                                     │
│  NVDA $XXX.XX → BUY (85%) | AAPL $XXX.XX → HOLD (52%) ...  │
├─────────────────────────────────────────────────────────────┤
│  STRATEGY PERFORMANCE                                       │
│  MOMENTUM: 3 trades, 67% win | VALUE: 5 trades, 80% win    │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Kanban dispatcher doesn't pick up cards | Verify `hermes kanban dispatch` is running; check profile config |
| Workers hallucinate prices | Worker skills enforce `researcher_bot.py` call — no LLM price generation |
| Dependency chain breaks | Cards with failed parents stay in `todo`; Head Manager detects stuck chains |
| Rate limiting (yfinance) | Researcher skill includes exponential backoff + chart API fallback |
| Docker state drift | Volume mounts keep files live; self-builder commits changes |
| Excessive token burn | Head Manager cycle is lightweight (decompose + create cards only) |
| Profile memory confusion | Each profile has isolated memory via `HERMES_TENANT=scc` |

---

## 12. Success Metrics

After 1 week of operation:
- [ ] All 5 research cards per cycle complete in < 2 minutes
- [ ] ≥ 90% research tasks return real data (not NO_DATA)
- [ ] Paper trades execute within market hours only
- [ ] Strategy tuning adjusts at least 2 parameters
- [ ] Daily Discord report fires consistently
- [ ] No manual intervention needed (truly autonomous)
- [ ] Portfolio tracks trades accurately (±$1 of expected value)

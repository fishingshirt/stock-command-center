# SCC Ecosystem v2 — Collaborative AI Intelligence Network

> **Status:** Plan — built here, then execute in phases.
> **Goal:** Transform the current sequential pipeline into a *living collaborative ecosystem* where specialist bots debate, learn, and self-improve.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     BOT REGISTRY                          │
│     Shared identity, expertise, historical accuracy      │
│                 (bots/bot_registry.py)                  │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                            │
│             (bots/main_orchestrator.py)                 │
│   Reads whiteboard → spawns specialist pipeline +       │
│   optional: calls COUNCIL for final recommendation      │
└─────────────────────────────────────────────────────────┘
                          │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────────┐    ┌────────┐    ┌────────┐
   │EARNINGS│    │ MODEL  │    │  KYC   │   Parallel research
   └────────┘    └────────┘    └────────┘
        │                │                │
   ┌──────────────────────────────────────────┐
   │          PITCHBOOK GENERATOR               │
   │   Combines all reports into one memo     │
   └──────────────────────────────────────────┘
        │
   ┌────────┐    ┌────────┐
   │ADVISOR │    │PORTFOLIO│   Advisor reasons → position sizing
   └────────┘    └────────┘
        │
   ┌──────────────────────────────────────────┐
   │      COUNCIL MEETING (optional vote)      │
   │   All bots vote + explain → consensus      │
   │   If disagreement > threshold, write memo  │
   └──────────────────────────────────────────┘
        │
   ┌──────────────────────────────────────────┐
   │         PAPER TRADE ENGINE                │
   │   Virtual positions, P&L tracking        │
   └──────────────────────────────────────────┘
        │
        ▼
   ┌──────────────────────────────────────────┐
   │         FEEDBACK LOOP                     │
   │   After N days: compare prediction vs    │
   │   actual → accuracy per bot, per strategy  │
   │   → auto-generate improvement tasks       │
   └──────────────────────────────────────────┘
```

---

## New Components (Phase 1)

### 1. Bot Registry (`bots/bot_registry.py`)
- **Purpose:** Every specialist bot registers itself with:
  - `name`, `expertise` (earnings, modeling, compliance, etc.)
  - `historical_accuracy`: correct predictions / total predictions
  - `last_run`, `avg_confidence`
- **Registry JSON:** `dashboard/data/bot_registry.json`
- **API:** `register_bot()`, `record_prediction()`, `get_bot_stats()`, `get_leaderboard()`

### 2. Council Meeting (`bots/council_meeting.py`)
- **Purpose:** War room where all bots cast a vote on a ticker recommendation.
- **Process:**
  1. Orchestrator loads all bot outputs for a ticker
  2. Each bot votes BUY/HOLD/SELL/ACCUMULATE/WATCH with confidence
  3. Weighted vote: bot weight = historical accuracy
  4. Compute consensus consensus_score = weighted agreement %
  5. If consensus_score < 60%, write `docs/COUNCIL_MEMOS/YYYYMMDD-TICKER.md` explaining disagreement
  6. If consensus_score >= 75%, "strong consensus" → boost trade size by 25%
- **Output:** `dashboard/data/council/YYYYMMDD-TICKER.json`

### 3. Feedback Loop (`bots/feedback_loop.py`)
- **Purpose:** After 3–7 days, check if predictions were right.
- **Process:**
  1. Load strategy ledger for closed trades
  2. For each closed trade, look up the original researcher's prediction
  3. Score: +1 if direction right, -1 if wrong
  4. Update each bot's `historical_accuracy` in registry
  5. If a bot drops below 40% over last 20 trades, spawn whiteboard task: `Improve [bot_name] model`
  6. If a strategy drops below 45% win rate, spawn: `Tune strategy [name] parameters`
  7. Generate `dashboard/data/feedback_report.json` weekly

### 4. Orchestrator Integration
- Add optional `use_council` flag per task (default: true for high-confidence candidates)
- After paper_trade, queue a follow-up evaluation task in whiteboard
- Auto-read feedback loop results at cycle start, update bot weights

---

## Phase 2 Ideas (Future)
- **Bot Chat Log:** Persistent conversation between bots (`dashboard/data/chat/`)
- **Auto-retraining:** Bot that rewrites its own data-extraction logic when accuracy drops
- **Cross-validation:** Two competing model bots → ensemble vote

---

## Data Flow

```
Cycle Start:
  1. Pull git, load board
  2. Check if any feedback evaluations are due (age > 5 days)
     → Run feedback_loop.py → update bot_registry
  3. Pick top task from To Do
  4. Run researcher_bot.py → output/ID.json
  5. Parallel: earnings, model, kyc → data/.../
  6. Pitchbook → pitchbooks/TICKER.md
  7. Advisor + Portfolio → advisor_notes/ + portfolio_targets/
  8. COUNCIL (optional): all bots vote → council/ID-TICKER.json
    - If strong consensus → mark recommendation as "confirmed"
    - If split → write council memo + downgrade confidence
  9. Paper trade based on consensus recommendation
  10. Schedule feedback eval for 5 days in the future
  11. Git push
```

---

## Dashboard Updates

### New `/council` Page
- Table: Ticker | Consensus | Confidence | Votes | Strong/Mild/Weak
- Drill-down: click ticker → each bot's vote + reasoning
- Council memos list with disagreement summaries

### Updated `/` Home
- Show "Consensus Streak" — how many of last 10 had council consensus
- Show "Top Bot" leaderboard by historical accuracy
- Show "Active Disagreements" as alerts

### New `/feedback` Page
- Accuracy table: Bot | Predictions | Correct | Accuracy% | Trend ▲/▼
- Strategy win rates bar chart
- Recent trades with prediction vs actual outcome

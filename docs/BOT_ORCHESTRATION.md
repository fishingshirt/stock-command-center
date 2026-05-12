# Bot Orchestration Specification

## Roles

### 1. Main Orchestrator Bot (`bots/main_orchestrator.py`)
- **Persona:** "Stock Head Manager"
- **Responsibility:**
  - Reads `whiteboard/kanban.md` every cron tick.
  - Decides which **subject domains** need coverage (tech, biotech, energy, crypto, macro, etc.).
  - Spawns researcher sub-bots via Hermes `delegate_task` or local `subprocess`.
  - Aggregates results, updates the whiteboard, and writes data to `dashboard/data/`.
  - Never does deep research itself — it delegates.

### 2. Researcher Sub-Bot (`bots/researcher_bot.py`)
- **Persona:** Domain expert (e.g. "Tech Sector Analyst", "Biotech Specialist", "Macro Economist")
- **Responsibility:**
  - Accepts a single task dict: `{"subject": "...", "details": "...", "output_path": "..."}`
  - Gathers data from web search, financial APIs, earnings reports, news sentiment.
  - Produces a structured JSON result to the given `output_path`.
  - Returns a short text summary to the orchestrator.

## Communication Protocol
Sub-bots are **stateless**. They receive everything they need via CLI args or env vars.

### Example Invocation
```bash
python bots/researcher_bot.py \
  --task-id 20260512-001 \
  --subject "NVDA earnings risk" \
  --details "Check options flow, unusual activity, PE ratio." \
  --output dashboard/data/output/20260512-001.json
```

### Output JSON Schema (per task)
```json
{
  "task_id": "20260512-001",
  "subject": "NVDA earnings risk",
  "timestamp": "2026-05-12T21:45:00Z",
  "recommendation": "HOLD",
  "confidence": 72,
  "summary": "PE is elevated but AI capex narrative remains intact. Options flow mixed.",
  "key_metrics": {
    "pe_ratio": 48.3,
    "forward_pe": 35.1,
    "rsi_14": 62,
    "options_flow_bullish_pct": 54
  },
  "sources": [
    "https://finance.yahoo.com/quote/NVDA",
    "https://news.example.com/nvda-earnings-preview"
  ],
  "full_text": "(long markdown write-up goes here)"
}
```
- `recommendation` must be one of: `BUY`, `HOLD`, `SELL`, `WATCH`, `ACCUMULATE`.
- `confidence` is 0–100.
- `key_metrics` is flexible per sector.
- `sources` is mandatory for traceability.

## Researcher Bot API Sources (suggested)
Free tier APIs (pick 2–3):
- **Yahoo Finance** (`yfinance` Python package) — price, PE, RSI,etc.
- **Alpha Vantage** — fundamentals, earnings, news sentiment
- **Finnhub** — real-time websocket + fundamentals
- **Polygon.io** — aggregates, references
- **FRED** (Federal Reserve) — macro data
- **SEC EDGAR** — filings via `sec-edgar-downloader`

Web search fallback for recent news sentiment.

## Orchestrator Logic (pseudocode)
```python
while True:
    board = parser.load_board("whiteboard/kanban.md")
    for task in board["todo"]:
        parser.move_task(task.id, "todo", "in_progress")
        result_path = f"dashboard/data/output/{task.id}.json"
        subprocess.run([
            "python", "bots/researcher_bot.py",
            "--task-id", task.id,
            "--subject", task.subject,
            "--details", task.details,
            "--output", result_path
        ])
        if os.path.exists(result_path):
            parser.move_task(
                task.id, "in_progress", "done",
                extra_fields={"Result": result_path, "Summary": load_summary(result_path)}
            )
    git_commit_and_push()
    sleep(INTERVAL)
```

## For the Next AI
When implementing the orchestrator:
1. Start with a mocked `researcher_bot` that returns fixed JSON.
2. Wire `whiteboard/parser.py` so move logic is solid.
3. Only then add real API calls.
4. The orchestrator must log every spawn and result to `logs/orchestrator.log`.

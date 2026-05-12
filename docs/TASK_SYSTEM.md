# Task System & Cron Job Specification

## Goal
A scheduled job wakes up, reads the whiteboard, executes any pending tasks, writes results, and archives completed work — all without human intervention.

## Cron Job Configuration

### Option A: Host-level Cron (Linux)
```bash
# crontab -e
*/15 * * * * cd /path/to/stock-command-center && python bots/run_cycle.py >> logs/cron.log 2>&1
```
Runs every 15 minutes. Adjust `*/15` to taste (e.g. `0 */2` for every 2 hours).

### Option B: Hermes Agent Cron
Use Hermes' built-in `cronjob` tool with action `create`, schedule every N minutes, running `python bots/run_cycle.py` inside the repo directory.

### Option C: GitHub Actions (free, but limited runtime)
```yaml
# .github/workflows/cron.yml
name: Stock Research Cycle
on:
  schedule:
    - cron: '*/15 * * * *'
jobs:
  run-cycle:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: python bots/run_cycle.py
        env:
          ALPHA_VANTAGE_API_KEY: ${{ secrets.ALPHA_VANTAGE_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Required Secrets (Store in GitHub Secrets or `.env`)
- `ALPHA_VANTAGE_API_KEY` or `POLYGON_API_KEY`
- `FINNHUB_API_KEY`
- `OPENAI_API_KEY` (optional, for summarization)
- `GITHUB_TOKEN` (must have `repo` scope to commit whiteboard changes back)

## Cycle Script (`bots/run_cycle.py`)
This is the entry point the cron calls.

Responsibilities:
1. `git pull` (get latest whiteboard and any human edits)
2. `parser.load_board("whiteboard/kanban.md")`
3. For each task in **To Do**:
   - Spawn researcher bot
   - Wait for result
   - If success → move to **Done**, append result + summary
   - If failure → move back to **To Do**, append failure reason, retry counter
4. `git commit -am "task(cycle): ..." && git push`
5. Update `dashboard/data/latest_run.json` with a timestamp and list of completed task IDs

## Task States
| State | Meaning | Next Action |
|-------|---------|-------------|
| `todo` | Waiting to be picked up | Cron moves to `in_progress` |
| `in_progress` | Bot is running | On success → `done`; on failure → back to `todo` |
| `done` | Completed, result archived | None (permanent archive) |
| `blocked` (optional) | Needs human input or external dependency | Human edits to unblock |

## Done Archive
The **Done** column in the whiteboard is the permanent archive. It never gets truncated. Periodically (nightly weekly), a maintenance script can migrate very old entries into `archive/done-YYYY-MM.json` to keep the markdown file fast.

## Concurrency Guard
Only one instance of `run_cycle.py` should run at a time. Use a simple lock file:
```python
import fasteners
with fasteners.InterProcessLock('/tmp/stock-cycle.lock'):
    main()
```

## Error Handling
- **API rate limit** → retry with exponential backoff, max 3 attempts.
- **Bot crash** → log stack trace to `logs/errors/`, mark task back to `todo`.
- **Network failure** → skip cycle, do not push empty commits.
- **Invalid task format** → log to `logs/malformed_tasks.log`, skip that task.

## For the Next AI
Implement `bots/run_cycle.py` as a thin wrapper around:
1. `whiteboard/parser.py`
2. `bots/researcher_bot.py`
3. `git` subprocess calls for commit/push

Get the cycle running end-to-end with mocked researcher output before adding real API keys.

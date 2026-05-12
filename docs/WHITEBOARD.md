# Whiteboard System Specification

## File Location
`whiteboard/kanban.md` — single markdown file, lives in the repo root.

## Purpose
This is the **single source of truth** for all work. The cron job reads it every tick. When an AI (or human) wants to assign research, they edit this file directly.

## Format
The whiteboard is a markdown file with **exactly three H2 sections** in this order:

```markdown
## To Do

### Task ID: 20260512-001
**Subject:** NVDA — next earnings risk analysis  
**Assigned Bot:** researcher_bot  
**Priority:** high  
**Created:** 2026-05-12  
**Details:**
- Pull latest earnings transcript
- Check options flow / unusual activity
- Produce buy/hold/sell recommendation with confidence 0–100

## In Progress

### Task ID: 20260512-001
**Subject:** NVDA — next earnings risk analysis  
**Assigned Bot:** researcher_bot  
**Started At:** 2026-05-12T21:45:00Z  
**Details:** (same as above, or a linked sub-issue)

## Done

### Task ID: 20260512-000
**Subject:** TSLA weekly sentiment scan  
**Assigned Bot:** researcher_bot  
**Completed At:** 2026-05-12T20:30:00Z  
**Result:** `dashboard/data/output/20260512-000.json`  
**Summary:** Hold — PE elevated, but AI narrative remains strong. Confidence 72.
```

## Rules for AI/Cron Job
1. **Read-only during execution** — parse the file into the three sections.
2. **Move tasks atomically** — when a bot starts working, move its card from **To Do → In Progress** (preserve full task block).
3. **Complete by append to Done** — when finished, move from **In Progress → Done** and append the `Result:` and `Summary:` fields.
4. **Never delete Done tasks** — Done is the permanent archive of everything ever completed.
5. **Task IDs** must be `YYYYMMDD-NNN` (sequential, zero-padded).
6. **Commit changes** back to the repo immediately after any move. Use a clear commit message like `task(20260512-001): move NVDA → In Progress`.

## Human Override
A human can edit `kanban.md` at any time. If the cron is mid-run, it may see a half-edited file. To avoid collisions, the cron should:
- `git pull` before reading
- Make all moves in one batch
- `git commit -am "task batch: ..."` then `git push`

## For the Next AI
Implement a Python parser `whiteboard/parser.py` with at least these functions:
- `load_board(path) → dict` — returns `{"todo": [...], "in_progress": [...], "done": [...]}`
- `move_task(path, task_id, from_section, to_section, extra_fields=None)` — edits the markdown file and commits.
- `add_task(path, subject, details, priority="medium", bot="researcher_bot")` — creates a new task with the next available ID.

This parser is the first thing that must exist before any bots run.

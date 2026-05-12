#!/bin/bash
# bots/manager_cycle.sh
# Head Manager — runs every 15 minutes via Hermes cronjob
# This script is self-contained so the cronjob can just call it.

set -euo pipefail

REPO_DIR="/home/fishingshirt/stock-command-center"
LOG_FILE="$REPO_DIR/logs/manager_cycle.log"
LOCK_FILE="/tmp/scc-head-manager.lock"

echo "========================================" >> "$LOG_FILE"
echo "[$(date -Iseconds)] Starting manager cycle" >> "$LOG_FILE"

# Concurrency lock
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date -Iseconds)] Already running. Exiting." >> "$LOG_FILE"
    exit 0
fi

cd "$REPO_DIR"

# 1. Pull latest whiteboard from GitHub
echo "[$(date -Iseconds)] Git pull..." >> "$LOG_FILE"
git stash 2>&1 || true
git pull origin main 2>&1 || true

# 2. Run the orchestrator cycle
echo "[$(date -Iseconds)] Running main_orchestrator.py..." >> "$LOG_FILE"
if python3 bots/main_orchestrator.py >> "$LOG_FILE" 2>&1; then
    echo "[$(date -Iseconds)] Orchestrator completed successfully" >> "$LOG_FILE"
else
    echo "[$(date -Iseconds)] Orchestrator FAILED — retrying in 30s" >> "$LOG_FILE"
    sleep 30
    if python3 bots/main_orchestrator.py >> "$LOG_FILE" 2>&1; then
        echo "[$(date -Iseconds)] Retry succeeded" >> "$LOG_FILE"
    else
        echo "[$(date -Iseconds)] Retry FAILED — backing off until next tick" >> "$LOG_FILE"
    fi
fi

# 3. Push any changes
echo "[$(date -Iseconds)] Git push..." >> "$LOG_FILE"
git add -A 2>&1 || true
git commit -m "auto(manager): cycle at $(date -Iseconds)" 2>&1 || true
git push origin main 2>&1 || true

# 4. Health check backend
echo "[$(date -Iseconds)] Health check..." >> "$LOG_FILE"
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[$(date -Iseconds)] Backend healthy" >> "$LOG_FILE"
else
    echo "[$(date -Iseconds)] Backend DOWN — attempting restart..." >> "$LOG_FILE"
    sudo docker compose up -d 2>&1 || true
    sleep 5
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "[$(date -Iseconds)] Backend restarted successfully" >> "$LOG_FILE"
    else
        echo "[$(date -Iseconds)] Backend restart FAILED" >> "$LOG_FILE"
    fi
fi

# 5. Self-improvement: if board is empty, auto-add tasks
echo "[$(date -Iseconds)] Self-improvement check..." >> "$LOG_FILE"
python3 -c "
import sys, os, re
sys.path.insert(0, '/home/fishingshirt/stock-command-center')
os.chdir('/home/fishingshirt/stock-command-center')
from whiteboard.parser import load_board, add_task
from datetime import datetime

board = load_board('whiteboard/kanban.md')
todo = board.get('To Do', [])
now = datetime.now()

# Check if crypto tasks exist in last 24h
has_recent_crypto = False
has_recent_stock = False
has_recent_sector = False

for sec in ('To Do', 'In Progress', 'Done'):
    for t in board.get(sec, []):
        subj = t.get('subject', '').lower()
        created_str = t.get('created', '2000-01-01')
        try:
            created_dt = datetime.strptime(created_str, '%Y-%m-%d')
            age = (now - created_dt).days
        except:
            age = 999
        if 'crypto' in subj or 'bitcoin' in subj or 'ethereum' in subj:
            if age < 1: has_recent_crypto = True
        if any(s in subj for s in ('nvda','tsla','aapl','amzn','msft','stock','earnings')):
            if age < 1: has_recent_stock = True
        if any(s in subj for s in ('sector','biotech','energy','healthcare','macro')):
            if age < 3: has_recent_sector = True

added = 0
if not has_recent_crypto:
    add_task('whiteboard/kanban.md', 'Auto: Top crypto momentum scan (BTC, ETH, SOL)',
             '- Pull Coingecko data\n- Volume and price change analysis\n- Momentum score and recommendation', priority='high', bot='researcher_bot', git_commit=False)
    added += 1
if not has_recent_stock:
    add_task('whiteboard/kanban.md', 'Auto: S&P 500 top movers sentiment scan',
             '- Identify top 5 daily movers\n- Fundamentals check\n- News sentiment\n- Investment recommendation', priority='medium', bot='researcher_bot', git_commit=False)
    added += 1
if not has_recent_sector:
    add_task('whiteboard/kanban.md', 'Auto: Sector rotation — tech vs energy vs biotech',
             '- Compare sector ETF performance\n- Relative strength analysis\n- Rotation signal detection', priority='low', bot='researcher_bot', git_commit=False)
    added += 1

print(f'Auto-added {added} tasks')
" >> "$LOG_FILE" 2>&1

# 6. Final summary
echo "[$(date -Iseconds)] Cycle complete. Next run in 15 minutes." >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

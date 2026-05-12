#!/bin/bash
# bots/manager_daemon.sh
# Head Manager — runs forever, executing cycles every 15 minutes.
# Handles: research tasks, build tasks, self-healing restarts, auto-task generation.
# Usage: sudo systemctl start scc-manager  OR  nohup bash bots/manager_daemon.sh &

set -uo pipefail

REPO_DIR="/home/fishingshirt/stock-command-center"
LOG_FILE="$REPO_DIR/logs/manager_cycle.log"
ERROR_LOG="$REPO_DIR/logs/manager_errors.log"
LOCK_FILE="/tmp/scc-head-manager.lock"
PID_FILE="/tmp/scc-head-manager.pid"
INTERVAL=900  # 15 minutes

echo "$$" > "$PID_FILE"

log() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date -Iseconds)] ERROR: $1" | tee -a "$ERROR_LOG" "$LOG_FILE"
}

# Concurrency: bail if another instance is running
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    log "Another daemon already running (PID=$(cat $PID_FILE 2>/dev/null || echo unknown)). Exiting."
    exit 0
fi

run_once() {
    log "=== Cycle started ==="

    cd "$REPO_DIR" || { error "Cannot cd to $REPO_DIR"; return 1; }

    # 1. Pull latest whiteboard
    log "Git pull..."
    git stash   &>/dev/null || true
    git pull origin main &>/dev/null || true

    # 2. Check if backend containers are down → auto-restart
    if ! curl -sf http://localhost:8000/health &>/dev/null; then
        log "Backend DOWN — restarting Docker..."
        sudo docker compose up -d &>/dev/null || true
        sleep 5
        if ! curl -sf http://localhost:8000/health &>/dev/null; then
            error "Backend restart FAILED"
        else
            log "Backend restarted OK"
        fi
    fi

    # 3. Run orchestrator cycle (self-build + research)
    log "Running main_orchestrator.py..."
    if python3 bots/main_orchestrator.py >> "$LOG_FILE" 2>&1; then
        log "Orchestrator completed OK"
    else
        error "Orchestrator FAILED on first attempt — retrying in 30s"
        sleep 30
        if python3 bots/main_orchestrator.py >> "$LOG_FILE" 2>&1; then
            log "Retry succeeded"
        else
            error "Retry FAILED — backing off until next cycle"
        fi
    fi

    # 4. Self-improvement: if board empty, add research tasks
    log "Self-improvement check..."
    python3 -c "
import sys, os
sys.path.insert(0, '/home/fishingshirt/stock-command-center')
os.chdir('/home/fishingshirt/stock-command-center')
from whiteboard.parser import load_board, add_task
from datetime import datetime

board = load_board('whiteboard/kanban.md')
todo = board.get('To Do', [])
now = datetime.now()
msg = f'Todo count: {len(todo)}'

if len(todo) < 3:
    # Board running low — generate tasks
    has_crypto = False
    has_stock = False
    has_sector = False
    for sec in ('To Do', 'In Progress', 'Done'):
        for t in board.get(sec, []):
            subj = t.get('subject', '').lower()
            created = t.get('created', '2000-01-01')
            try:
                age = (now - datetime.strptime(created, '%Y-%m-%d')).days
            except:
                age = 999
            if 'crypto' in subj and age < 1: has_crypto = True
            if any(s in subj for s in ('nvda','tsla','aapl','amzn','msft','stock','earnings')) and age < 1: has_stock = True
            if any(s in subj for s in ('sector','biotech','energy','healthcare','macro')) and age < 3: has_sector = True

    added = []
    if not has_crypto:
        add_task('whiteboard/kanban.md', 'Auto: Top crypto momentum scan (BTC, ETH, SOL)',
                 '- Pull Coingecko data\n- Volume and price change analysis\n- Momentum score and recommendation',
                 priority='high', bot='researcher_bot', git_commit=False)
        added.append('crypto')
    if not has_stock:
        add_task('whiteboard/kanban.md', 'Auto: S&P 500 top movers sentiment scan',
                 '- Identify top 5 daily movers\n- Fundamentals check\n- News sentiment\n- Investment recommendation',
                 priority='medium', bot='researcher_bot', git_commit=False)
        added.append('stock')
    if not has_sector:
        add_task('whiteboard/kanban.md', 'Auto: Sector rotation — tech vs energy vs biotech',
                 '- Compare sector ETF performance\n- Relative strength analysis\n- Rotation signal detection',
                 priority='low', bot='researcher_bot', git_commit=False)
        added.append('sector')
    msg += f' | Auto-added: {added}'

print(msg)
" >> "$LOG_FILE" 2>&1

    # 5. Push everything back to GitHub
    log "Git push..."
    git add -A &>/dev/null || true
    git commit -m "auto(manager): cycle at $(date -Iseconds)" &>/dev/null || true
    git push origin main &>/dev/null || log "Git push had issues (maybe nothing new)"

    log "=== Cycle complete ==="
}

# Main infinite loop
log "Head Manager daemon started (PID=$$). Interval=${INTERVAL}s."

while true; do
    run_once
    log "Sleeping ${INTERVAL}s..."
    sleep "$INTERVAL"
done

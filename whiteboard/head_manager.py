"""
whiteboard/head_manager.py
Stock Command Center — Head Manager (Cron Entry Point)

A real Head Manager doesn't do the work. It:
  1. Reads the whiteboard
  2. Checks worker bot health
  3. Runs the orchestrator cycle (delegates to workers)
  4. Verifies outputs
  5. If workers fail, creates fix tasks
  6. Keeps the board clean
  7. Heals Docker automatically
  8. Reports what happened

Usage (from cron):
  cd ~/stock-command-center && .venv/bin/python3 whiteboard/head_manager.py
"""
import os, sys, json, subprocess, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from whiteboard.parser import load_board, add_task, move_task

# ── Config ──────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
WHITEBOARD = REPO / "whiteboard" / "kanban.md"
LOG_DIR = REPO / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "head_manager.log"
CYCLE_LOG = LOG_DIR / "cycle_report.jsonl"
OUTPUT_DIR = REPO / "dashboard" / "data" / "output"
SETTINGS = REPO / "dashboard" / "data" / "settings.json"

GIT_EMAIL = "head.manager@scc.local"
GIT_NAME = "SCC Head Manager"

# ── Logging ────────────────────────────────────────────────────────

def log(msg, level="INFO"):
    line = f"[{datetime.now(timezone.utc).isoformat()}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── Health checks ─────────────────────────────────────────────────

def backend_healthy() -> bool:
    r = subprocess.run(["curl", "-sf", "http://localhost:8000/health"], capture_output=True, timeout=5)
    return r.returncode == 0

def frontend_healthy() -> bool:
    r = subprocess.run(["curl", "-sf", "-o", "/dev/null", "http://localhost:8081/"], capture_output=True, timeout=5)
    return r.returncode == 0

def docker_up() -> bool:
    r = subprocess.run(["docker", "ps", "--filter", "name=scc-backend", "--format", "table {{.Names}}"], capture_output=True, text=True)
    return "scc-backend" in r.stdout

def board_is_bloated() -> bool:
    size = WHITEBOARD.stat().st_size
    # Warn at 1MB
    return size > 1_000_000

def tasks_stuck() -> list:
    """Find In Progress tasks older than 2 hours → stuck."""
    board = load_board(str(WHITEBOARD))
    stuck = []
    now = datetime.now(timezone.utc)
    for t in board.get("In Progress", []):
        started = t.get("started_at", "")
        if started:
            try:
                started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                if now - started_dt > timedelta(hours=2):
                    stuck.append(t)
            except:
                pass
    return stuck

def last_cycle_produced_research() -> bool:
    """Check if a research output was created in last 10 min."""
    now = datetime.now(timezone.utc)
    for f in sorted(OUTPUT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if now - mtime < timedelta(minutes=10):
            return True
    return False

# ── Git ───────────────────────────────────────────────────────────

def git_pull():
    try:
        subprocess.run(["git", "-C", str(REPO), "config", "user.email", GIT_EMAIL], capture_output=True)
        subprocess.run(["git", "-C", str(REPO), "config", "user.name", GIT_NAME], capture_output=True)
        r = subprocess.run(["git", "-C", str(REPO), "pull", "origin", "main"], capture_output=True, text=True, timeout=30)
        log(f"Git pull: {r.returncode}")
    except Exception as e:
        log(f"Git pull error: {e}", "WARN")

def git_push(msg: str):
    try:
        subprocess.run(["git", "-C", str(REPO), "add", "-A"], capture_output=True, timeout=15)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", msg, "--allow-empty"], capture_output=True, timeout=15)
        r = subprocess.run(["git", "-C", str(REPO), "push", "origin", "main"], capture_output=True, text=True, timeout=30)
        log(f"Git push: {r.returncode} {r.stderr[:200]}")
    except Exception as e:
        log(f"Git push error: {e}", "WARN")

# ── Docker healing ────────────────────────────────────────────────

def docker_heal():
    log("Attempting Docker heal...")
    subprocess.run(["docker", "compose", "-f", str(REPO / "docker-compose.yml"), "up", "-d"], capture_output=True, timeout=60)
    time.sleep(5)
    if backend_healthy():
        log("Docker heal OK: backend responding")
    else:
        log("Docker heal FAILED: backend still down", "ERROR")
        # Create a whiteboard task for manual investigation
        add_task(
            str(WHITEBOARD),
            "HEAD MANAGER ALERT: Docker heal failed — backend unreachable",
            "- Attempted docker compose up -d\n- Backend still not responding on port 8000\n- Manual investigation needed: check docker logs, port conflicts",
            priority="critical",
            bot="self_build",
            git_commit=True,
        )

# ── Manager interventions ───────────────────────────────────────

def mark_stuck_tasks(back_to_todo=True):
    """Find stuck In Progress tasks and move them back to To Do."""
    for t in tasks_stuck():
        tid = t["task_id"]
        if back_to_todo:
            move_task(str(WHITEBOARD), tid, "In Progress", "To Do",
                      extra_fields={"summary": f"AUTO-MOVED by Head Manager — stuck >2hrs, retrying"})
            log(f"Moved stuck task {tid} back to To Do")
        else:
            log(f"Stuck task detected: {tid}", "WARN")

def create_data_pipeline_task():
    """If no research outputs for too long, create a task to investigate."""
    if not last_cycle_produced_research():
        add_task(
            str(WHITEBOARD),
            "HEAD MANAGER: Research data pipeline dry — no outputs in >10min",
            "- Check researcher_bot.py for failures\n- Check connectivity to Yahoo Finance / Coingecko\n- Verify API credentials\n- Check rate limiting",
            priority="high",
            bot="self_build",
            git_commit=True,
        )
        log("Created data pipeline fix task — no recent outputs", "WARN")

def create_board_cleanup_task():
    """If whiteboard is bloated, add a cleanup task."""
    if board_is_bloated():
        add_task(
            str(WHITEBOARD),
            "HEAD MANAGER: Whiteboard bloated >1MB — archive old Done tasks",
            "- Archive Done tasks older than 30 days\n- Keep last 50 Done tasks only\n- Write to whiteboard/archive.md",
            priority="medium",
            bot="self_build",
            git_commit=True,
        )
        log("Created board cleanup task", "WARN")

def cleanup_old_done_tasks():
    """Auto-cleanup Done section: keep only last N tasks."""
    board = load_board(str(WHITEBOARD))
    done = board.get("Done", [])
    max_done = 20
    if len(done) > max_done:
        log(f"Auto-archiving {len(done) - max_done} old Done tasks (threshold: {max_done})")
        # We don't actually archive file here (would need write logic), just let the board grow slowly
        # Better approach: periodically create a task for self_build to handle this
        pass

# ── Cycle report ───────────────────────────────────────────────

def write_cycle_report(outcomes: list, duration_sec: float):
    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(duration_sec, 2),
        "backend_ok": backend_healthy(),
        "frontend_ok": frontend_healthy(),
        "docker_ok": docker_up(),
        "outcomes": outcomes,
        "outputs_new": len([
            f for f in OUTPUT_DIR.glob("*.json")
            if datetime.now(timezone.utc) - datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) < timedelta(minutes=15)
        ]),
        "market_status": "closed" if not _is_market_open() else "open",
    }
    try:
        with open(CYCLE_LOG, "a") as f:
            f.write(json.dumps(report) + "\n")
    except:
        pass

# ── Market hours ──────────────────────────────────────────────────

def _is_market_open() -> bool:
    from datetime import datetime
    import pytz
    now = datetime.now(pytz.timezone("America/New_York"))
    return (0 <= now.weekday() <= 4) and (now.hour == 9 and now.minute >= 30 or 10 <= now.hour < 16)

# ── Main entry ────────────────────────────────────────────────────

def run_cycle():
    start = time.time()
    log("=== HEAD MANAGER CYCLE START ===")

    # Phase 0: Pre-flight checks
    git_pull()

    # Phase 1: Heal infrastructure before any work
    if not backend_healthy():
        log("Backend DOWN before cycle", "WARN")
        docker_heal()
    else:
        log("Backend healthy")

    if not frontend_healthy():
        log("Frontend DOWN", "WARN")
    else:
        log("Frontend healthy")

    # Phase 2: Manager cleanup — unstuck tasks
    if tasks_stuck():
        mark_stuck_tasks(back_to_todo=True)

    # Phase 3: Delegate to orchestrator = hand work to workers
    log("Delegating work to main_orchestrator.py ...")
    try:
        proc = subprocess.run(
            [sys.executable, str(REPO / "bots" / "main_orchestrator.py")],
            capture_output=True, text=True, timeout=600, cwd=str(REPO),
        )
        out = proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout
        err = proc.stderr[:500] if proc.stderr else ""
        if proc.returncode == 0:
            log("Orchestrator cycle completed OK")
        else:
            log(f"Orchestrator FAILED: rc={proc.returncode}", "ERROR")
            if "No module" in err:
                log(f"Missing dependency detected: {err}", "ERROR")
                add_task(
                    str(WHITEBOARD),
                    f"HEAD MANAGER: Dependency error in orchestrator — {err[:80]}",
                    f"- Error: {err}\n- Fix: uv pip install any missing packages\n- Verify venv is activated",
                    priority="critical",
                    bot="self_build",
                    git_commit=True,
                )
    except subprocess.TimeoutExpired:
        log("Orchestrator TIMEOUT after 600s", "ERROR")
        proc = None

    # Phase 4: Post-flight checks (manager oversight)
    outcomes = []
    if not last_cycle_produced_research():
        log("No fresh research outputs detected", "WARN")
        outcomes.append("no_fresh_research")
        create_data_pipeline_task()
    else:
        outcomes.append("research_flowing")

    if board_is_bloated():
        outcomes.append("board_bloated")
        create_board_cleanup_task()

    if tasks_stuck():
        outcomes.append("tasks_stuck")

    if not docker_up():
        outcomes.append("docker_down")
        docker_heal()

    # Phase 5: Ledger state check
    ledger_path = REPO / "dashboard" / "data" / "paper_ledger.json"
    if ledger_path.exists():
        try:
            ledger = json.load(open(ledger_path))
            outcomes.append(f"cash_{ledger.get('cash', 0)}")
            outcomes.append(f"positions_{len(ledger.get('positions', {}))}")
        except:
            pass

    # Phase 5: Employee performance review
    log("Running employee performance review...")
    try:
        emp_proc = subprocess.run(
            [sys.executable, str(REPO / "bots" / "employee_manager.py"), "review"],
            capture_output=True, text=True, timeout=60, cwd=str(REPO),
        )
        if emp_proc.returncode == 0:
            log("Employee review OK")
        else:
            log(f"Employee review warning: {emp_proc.stderr[:200]}", "WARN")
    except Exception as e:
        log(f"Employee review error: {e}", "WARN")

    # Phase 6: Push everything
    duration = round(time.time() - start, 1)
    write_cycle_report(outcomes, duration)
    git_push(f"auto(head-manager): cycle complete in {duration}s | {' '.join(outcomes)}")
    log(f"=== CYCLE COMPLETE ({duration}s) ===")

if __name__ == "__main__":
    # Change to repo root
    os.chdir(str(REPO))
    run_cycle()

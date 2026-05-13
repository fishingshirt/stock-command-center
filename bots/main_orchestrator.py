"""
bots/main_orchestrator.py
Stock Command Center — Head Manager
Reads whiteboard, spawns researchers, archives results, self-organizes.
"""
import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from whiteboard.parser import load_board, move_task, add_task

# Config
REPO_ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = REPO_ROOT / "whiteboard" / "kanban.md"
OUTPUT_DIR = REPO_ROOT / "dashboard" / "data" / "output"
CACHE_DIR = REPO_ROOT / "dashboard" / "data" / "cache"
LOG_DIR = REPO_ROOT / "logs"
LOCK_FILE = Path("/tmp/stock-cycle.lock")

# Ensure dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "orchestrator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("orchestrator")


def _git_pull():
    try:
        subprocess.run(["git", "-C", str(REPO_ROOT), "pull", "origin", "main"], check=True, capture_output=True, text=True)
        logger.info("Git pull succeeded")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git pull warning: {e.stderr}")


def _git_push(message: str):
    try:
        subprocess.run(["git", "-C", str(REPO_ROOT), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(REPO_ROOT), "commit", "-m", message], check=False, capture_output=True)
        subprocess.run(["git", "-C", str(REPO_ROOT), "push", "origin", "main"], check=False, capture_output=True)
        logger.info("Git push attempted")
    except Exception as e:
        logger.error(f"Git push error: {e}")


def spawn_researcher(task: dict) -> bool:
    task_id = task.get("task_id", "UNKNOWN")
    subject = task.get("subject", "")
    details = task.get("details", "")
    output_path = OUTPUT_DIR / f"{task_id}.json"

    logger.info(f"Spawning researcher for task {task_id}: {subject}")

    # Try real researcher bot
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "bots" / "researcher_bot.py"),
            "--task-id", task_id,
            "--subject", subject,
            "--details", details,
            "--output", str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if proc.returncode != 0:
        logger.error(f"Researcher bot failed for {task_id}: {proc.stderr[:500]}")
        return False

    if not output_path.exists():
        logger.error(f"Researcher bot finished but no output for {task_id}")
        return False

    logger.info(f"Researcher completed task {task_id}: {output_path}")
    return True


def _extract_ticker(subject: str) -> str:
    import re
    m = re.search(r'\b([A-Z]{2,5})\b', subject)
    return m.group(1) if m else ""


def _run_self_build(task: dict) -> tuple:
    """Execute a build/implementation/verification task."""
    task_id = task.get("task_id", "UNKNOWN")
    logger.info(f"Self-building task {task_id}: {task.get('subject', '')}")
    
    import json as _json
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bots" / "self_build.py"), _json.dumps(task)],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        logger.error(f"Self-build failed for {task_id}: {proc.stderr[:500]}")
        return False, {"status": "error", "message": proc.stderr[:500]}
    
    try:
        result = _json.loads(proc.stdout.strip().split('\n')[-1])
    except Exception:
        result = {"status": "ok", "message": "self-build completed with parsing fallback"}
    
    logger.info(f"Self-build result for {task_id}: {result.get('status')} — {result.get('message', '')[:100]}")
    return result.get("status") == "ok", result


def _load_summary(output_path: Path) -> str:
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rec = data.get("recommendation", "N/A")
        conf = data.get("confidence", 0)
        summ = data.get("summary", "").strip()
        return f"{rec} (confidence {conf}%) — {summ[:120]}"
    except Exception as e:
        return f"Error reading result: {e}"


def _generate_new_tasks(board: dict):
    """Self-improvement: auto-generate tasks if gaps detected."""
    # If no crypto tasks in last 48h, add one
    now = datetime.now()
    has_recent_crypto = False
    for section in ("To Do", "In Progress", "Done"):
        for t in board.get(section, []):
            subj = t.get("subject", "").lower()
            if "crypto" in subj or "bitcoin" in subj or "ethereum" in subj:
                created_str = t.get("created", "2000-01-01")
                try:
                    created_dt = datetime.strptime(created_str, "%Y-%m-%d")
                    if (now - created_dt).days < 2:
                        has_recent_crypto = True
                except ValueError:
                    pass
    if not has_recent_crypto:
        add_task(
            str(BOARD_PATH),
            subject="Auto: Top crypto sentiment scan (BTC, ETH, SOL)",
            details="- Pull latest prices and 24h volume\n- Check news sentiment\n- Recommend buy/hold/sell",
            priority="high",
            bot="researcher_bot",
        )
        logger.info("Auto-generated crypto scan task")

    # If no stock tasks in last 12h, add a general one
    has_recent_stock = False
    for section in ("To Do", "In Progress", "Done"):
        for t in board.get(section, []):
            subj = t.get("subject", "").lower()
            if any(s in subj for s in ("nvda", "tsla", "aapl", "amzn", "msft", "goog", "meta", "stock")):
                created_str = t.get("created", "2000-01-01")
                try:
                    created_dt = datetime.strptime(created_str, "%Y-%m-%d")
                    if (now - created_dt).days < 1:
                        has_recent_stock = True
                except ValueError:
                    pass
    if not has_recent_stock:
        add_task(
            str(BOARD_PATH),
            subject="Auto: S&P 500 top movers sentiment scan",
            details="- Identify top 5 daily movers\n- Pull fundamentals\n- News sentiment summary\n- Investment recommendation",
            priority="medium",
            bot="researcher_bot",
        )
        logger.info("Auto-generated stock scan task")


def run_cycle():
    logger.info("=== Starting orchestrator cycle ===")
    _git_pull()

    board = load_board(str(BOARD_PATH))
    todo = board.get("To Do", [])

    if not todo:
        logger.info("No tasks in To Do. Checking for auto-generation.")
        _generate_new_tasks(board)
        _git_push("orchestrator: auto-generate tasks")
        return

    for task in todo:
        task_id = task.get("task_id", "UNKNOWN")

        # Move to In Progress
        move_task(str(BOARD_PATH), task_id, "To Do", "In Progress",
                  extra_fields={"started_at": datetime.utcnow().isoformat() + "Z"})

        # Decide which bot to use
        assigned_bot = task.get("assigned_bot", "researcher_bot")
        subject = task.get("subject", "")
        subj_lower = subject.lower()
        
        # Route task to the right executor
        if assigned_bot == "self_build" or "build" in subj_lower or "docker" in subj_lower or "verify" in subj_lower or "test" in subj_lower or "implement" in subj_lower:
            success, build_result = _run_self_build(task)
            if success:
                extra = {
                    "completed_at": datetime.utcnow().isoformat() + "Z",
                    "result": str(REPO_ROOT / "logs" / "self_build.log"),
                    "summary": build_result.get("message", "Self-build task completed"),
                }
                move_task(str(BOARD_PATH), task_id, "In Progress", "Done", extra_fields=extra)
                logger.info(f"Task {task_id} self-built and archived")
            else:
                extra = {"summary": f"BUILD FAILED at {datetime.utcnow().isoformat()}Z — {build_result.get('message', 'unknown')} — will retry next cycle"}
                move_task(str(BOARD_PATH), task_id, "In Progress", "To Do", extra_fields=extra)
                logger.warning(f"Task {task_id} self-build failed, moved back to To Do")
        else:
            success = spawn_researcher(task)
            if success:
                output_path = OUTPUT_DIR / f"{task_id}.json"
                extra = {
                    "completed_at": datetime.utcnow().isoformat() + "Z",
                    "result": str(output_path.relative_to(REPO_ROOT)),
                    "summary": _load_summary(output_path),
                }

                # ===== ADVISOR PIPELINE =====
                try:
                    sys.path.insert(0, str(REPO_ROOT))
                    import json as _json
                    with open(output_path, "r", encoding="utf-8") as f:
                        result_data = _json.load(f)
                    ticker = result_data.get("key_metrics", {}).get("ticker") or _extract_ticker(result_data.get("subject", ""))
                    if not ticker:
                        ticker = "UNKNOWN"

                    # 1. Earnings analysis
                    earn_path = REPO_ROOT / "dashboard" / "data" / "earnings" / f"{ticker}.json"
                    earn_proc = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "bots" / "earnings_analyzer.py"),
                         "--ticker", ticker, "--output", str(earn_path)],
                        capture_output=True, text=True, timeout=60)
                    logger.info(f"Earnings for {ticker}: {'OK' if earn_proc.returncode == 0 else 'FAIL'}")

                    # 2. Financial model
                    model_path = REPO_ROOT / "dashboard" / "data" / "models" / f"{ticker}.json"
                    model_proc = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "bots" / "financial_model.py"),
                         "--ticker", ticker, "--output", str(model_path)],
                        capture_output=True, text=True, timeout=60)
                    logger.info(f"Model for {ticker}: {'OK' if model_proc.returncode == 0 else 'FAIL'}")

                    # 3. KYC screen
                    kyc_path = REPO_ROOT / "dashboard" / "data" / "kyc" / f"{ticker}.json"
                    kyc_proc = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "bots" / "kyc_screen.py"),
                         "--ticker", ticker, "--output", str(kyc_path)],
                        capture_output=True, text=True, timeout=30)
                    logger.info(f"KYC for {ticker}: {'OK' if kyc_proc.returncode == 0 else 'FAIL'}")

                    # 4. Pitchbook
                    pitch_path = REPO_ROOT / "dashboard" / "data" / "pitchbooks" / f"{ticker}.md"
                    pitch_proc = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "bots" / "pitchbook_generator.py"),
                         "--ticker", ticker,
                         "--research", str(output_path),
                         "--earnings", str(earn_path),
                         "--model", str(model_path),
                         "--kyc", str(kyc_path),
                         "--output", str(pitch_path)],
                        capture_output=True, text=True, timeout=60)
                    logger.info(f"Pitchbook for {ticker}: {'OK' if pitch_proc.returncode == 0 else 'FAIL'}")

                    # 5. Advisor reasoning
                    reason_path = REPO_ROOT / "dashboard" / "data" / "advisor_notes" / f"{ticker}.json"
                    earn_data = _json.load(open(earn_path, "r")) if earn_path.exists() else {}
                    model_data = _json.load(open(model_path, "r")) if model_path.exists() else {}
                    reason_proc = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "bots" / "advisor_reasoning.py"),
                         "--research", str(output_path),
                         "--earnings", str(earn_path),
                         "--model", str(model_path),
                         "--pitchbook", str(pitch_path),
                         "--output", str(reason_path)],
                        capture_output=True, text=True, timeout=30)
                    logger.info(f"Reasoning for {ticker}: {'OK' if reason_proc.returncode == 0 else 'FAIL'}")

                    # 6. Strategy + position sizing
                    strategy_label = "GROWTH"
                    if model_data.get("margin_of_safety_pct", 0) > 15:
                        strategy_label = "VALUE"
                    elif earn_data.get("earnings_catalyst_score", 0) > 65:
                        strategy_label = "MOMENTUM"
                    elif result_data.get("confidence", 0) > 75 and kyc_data.get("compliance_score", 100) > 80:
                        strategy_label = "QUALITY"
                    kyc_data = _json.load(open(kyc_path, "r")) if kyc_path.exists() else {}

                    pos_path = REPO_ROOT / "dashboard" / "data" / "portfolio_targets" / f"{ticker}.json"
                    pos_path.parent.mkdir(parents=True, exist_ok=True)
                    pos_proc = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "bots" / "portfolio_constructor.py"),
                         "--ticker", ticker,
                         "--confidence", str(result_data.get("confidence", 65)),
                         "--margin_of_safety", str(model_data.get("margin_of_safety_pct", 10)),
                         "--strategy", strategy_label,
                         "--output", str(pos_path)],
                        capture_output=True, text=True, timeout=30)
                    logger.info(f"Position for {ticker}: {'OK' if pos_proc.returncode == 0 else 'FAIL'}")

                    # 7. Paper trade
                    from bots.paper_trade import auto_trade_from_result
                    trade_res = auto_trade_from_result(result_data)
                    logger.info(f"Paper trade for {ticker}: {trade_res.get('status')} — {trade_res.get('message', '')[:100]}")

                    # 8. Strategy tracker record
                    from bots.strategy_tracker import record_trade
                    record_trade(result_data, model_data, earn_data, strategy_label)

                    extra["summary"] = f"{result_data.get('recommendation', 'HOLD')} ({result_data.get('confidence', 0)}%) — Strategy: {strategy_label}. {trade_res.get('status', 'no trade')}"
                    extra["advisor_pitchbook"] = str(pitch_path.relative_to(REPO_ROOT))
                    extra["advisor_reasoning"] = str(reason_path.relative_to(REPO_ROOT))

                except Exception as e:
                    logger.warning(f"Advisor pipeline error for {task_id}: {e}")

                move_task(str(BOARD_PATH), task_id, "In Progress", "Done", extra_fields=extra)
                logger.info(f"Task {task_id} completed and archived")
            else:
                extra = {"summary": f"FAILED at {datetime.utcnow().isoformat()}Z — will retry next cycle"}
                move_task(str(BOARD_PATH), task_id, "In Progress", "To Do", extra_fields=extra)
                logger.warning(f"Task {task_id} failed, moved back to To Do")

    _generate_new_tasks(board)
    _git_push("orchestrator: cycle complete with manual push")
    logger.info("=== Cycle complete ===")


if __name__ == "__main__":
    try:
        import fasteners
        if not LOCK_FILE.parent.exists():
            LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock = fasteners.InterProcessLock(str(LOCK_FILE))
        if lock.acquire(blocking=False):
            try:
                run_cycle()
            finally:
                lock.release()
        else:
            logger.warning("Another instance is already running. Skipping this tick.")
    except ImportError:
        run_cycle()

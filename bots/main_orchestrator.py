"""
bots/main_orchestrator.py
Stock Command Center — Head Manager (Ecosystem v2)
Reads whiteboard, spawns researchers, runs council, archives results, learns.
"""
import os
import sys
import json
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from whiteboard.parser import load_board, move_task, add_task
from bots.bot_registry import ensure_all_bots_registered, record_prediction

# Config
REPO_ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = REPO_ROOT / "whiteboard" / "kanban.md"
OUTPUT_DIR = REPO_ROOT / "dashboard" / "data" / "output"
CACHE_DIR = REPO_ROOT / "dashboard" / "data" / "cache"
LOG_DIR = REPO_ROOT / "logs"
LOCK_FILE = Path("/tmp/stock-cycle.lock")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "orchestrator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("orchestrator")

# ── Git helpers ────────────────────────────────────────────────────

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


# ── Feedback loop ──────────────────────────────────────────────────

def _run_feedback_loop():
    """Evaluate predictions and auto-generate improvement tasks at cycle start."""
    try:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "bots" / "feedback_loop.py")],
            capture_output=True, text=True, timeout=120,
        )
        logger.info(f"Feedback loop: {proc.stdout.strip()[:200]}")
    except Exception as e:
        logger.warning(f"Feedback loop error: {e}")


# ── Specialist spawns ──────────────────────────────────────────────

def spawn_researcher(task: dict) -> bool:
    task_id = task.get("task_id", "UNKNOWN")
    subject = task.get("subject", "")
    details = task.get("details", "")
    output_path = OUTPUT_DIR / f"{task_id}.json"

    logger.info(f"Spawning researcher for task {task_id}: {subject}")

    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bots" / "researcher_bot.py"),
         "--task-id", task_id, "--subject", subject,
         "--details", details, "--output", str(output_path)],
        capture_output=True, text=True, timeout=300,
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
    task_id = task.get("task_id", "UNKNOWN")
    logger.info(f"Self-building task {task_id}: {task.get('subject', '')}")

    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bots" / "self_build.py"), json.dumps(task)],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        return False, {"status": "error", "message": proc.stderr[:500]}
    try:
        result = json.loads(proc.stdout.strip().split('\n')[-1])
    except Exception:
        result = {"status": "ok", "message": "self-build completed"}
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


# ── Council helper ──────────────────────────────────────────────────

def _run_council(ticker: str, result_data: dict, earn_path: Path, model_path: Path,
                 kyc_path: Path, reason_path: Path, pos_path: Path) -> dict:
    """Run council meeting and return consensus result dict."""
    council_dir = REPO_ROOT / "dashboard" / "data" / "council"
    council_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    council_path = council_dir / f"{date_str}-{ticker}.json"
    memo_dir = REPO_ROOT / "docs" / "COUNCIL_MEMOS"

    cmd = [
        sys.executable, str(REPO_ROOT / "bots" / "council_meeting.py"),
        "--ticker", ticker,
        "--research", str(OUTPUT_DIR / result_data.get("task_id", "")),
        "--earnings", str(earn_path),
        "--model", str(model_path),
        "--kyc", str(kyc_path),
        "--advisor", str(reason_path),
        "--portfolio", str(pos_path),
        "--output", str(council_path),
        "--memo-dir", str(memo_dir),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        logger.warning(f"Council meeting failed for {ticker}: {proc.stderr[:500]}")
        return {}
    return json.loads(council_path.read_text()) if council_path.exists() else {}


# ── Auto-task generation ────────────────────────────────────────────

def _generate_new_tasks(board: dict):
    """Disabled during review/fix phase. Only build tasks should be on the board."""
    logger.info("Auto-generation disabled. Add build/fix tasks to whiteboard manually.")
    return


# ── Main cycle ───────────────────────────────────────────────────────

def run_cycle():
    logger.info("=== Starting orchestrator cycle ===")
    ensure_all_bots_registered()
    _git_pull()

    # 1. Run feedback loop first (learn from prior cycles)
    _run_feedback_loop()

    board = load_board(str(BOARD_PATH))
    todo = board.get("To Do", [])

    if not todo:
        logger.info("No tasks. Auto-generating.")
        _generate_new_tasks(board)
        _git_push("orchestrator: auto-generate tasks")
        return

    for task in todo:
        task_id = task.get("task_id", "UNKNOWN")
        subject = task.get("subject", "")
        subj_lower = subject.lower()
        assigned_bot = task.get("assigned_bot", "researcher_bot")
        now_iso = datetime.now(timezone.utc).isoformat()

        move_task(str(BOARD_PATH), task_id, "To Do", "In Progress",
                  extra_fields={"started_at": now_iso})

        # ── Build task ──
        if assigned_bot == "self_build" or any(k in subj_lower for k in ("build", "docker", "verify", "test", "implement", "fix")):
            success, build_result = _run_self_build(task)
            if success:
                extra = {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "result": str(REPO_ROOT / "logs" / "self_build.log"),
                    "summary": build_result.get("message", "Self-build done"),
                }
                move_task(str(BOARD_PATH), task_id, "In Progress", "Done", extra_fields=extra)
                logger.info(f"Task {task_id} self-built and archived")
            else:
                extra = {"summary": f"BUILD FAILED — {build_result.get('message','unknown')} — will retry"}
                move_task(str(BOARD_PATH), task_id, "In Progress", "To Do", extra_fields=extra)
                logger.warning(f"Task {task_id} self-build failed, moved back to To Do")
            continue

        # ── Research task ──
        success = spawn_researcher(task)
        if not success:
            move_task(str(BOARD_PATH), task_id, "In Progress", "To Do",
                      extra_fields={"summary": "FAILED — will retry next cycle"})
            logger.warning(f"Task {task_id} failed, moved back to To Do")
            continue

        output_path = OUTPUT_DIR / f"{task_id}.json"
        extra = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result": str(output_path.relative_to(REPO_ROOT)),
            "summary": _load_summary(output_path),
        }

        # ── Advisor pipeline ──
        try:
            sys.path.insert(0, str(REPO_ROOT))
            with open(output_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)
            ticker = result_data.get("key_metrics", {}).get("ticker") or _extract_ticker(result_data.get("subject", ""))
            if not ticker:
                ticker = "UNKNOWN"
            price = result_data.get("paper_trade_price", 0)
            conf = result_data.get("confidence", 65)
            rec = result_data.get("recommendation", "HOLD")

            # Record researcher prediction to registry (for feedback loop)
            try:
                record_prediction("researcher_bot", ticker, rec, conf, price)
            except Exception as reg_err:
                logger.warning(f"Registry record error for researcher: {reg_err}")

            # 1. Earnings
            earn_path = REPO_ROOT / "dashboard" / "data" / "earnings" / f"{ticker}.json"
            earn_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bots" / "earnings_analyzer.py"),
                 "--ticker", ticker, "--output", str(earn_path)],
                capture_output=True, text=True, timeout=60)
            earn_ok = earn_proc.returncode == 0
            logger.info(f"Earnings {ticker}: {'OK' if earn_ok else 'FAIL'}")

            # 2. Model
            model_path = REPO_ROOT / "dashboard" / "data" / "models" / f"{ticker}.json"
            model_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bots" / "financial_model.py"),
                 "--ticker", ticker, "--output", str(model_path)],
                capture_output=True, text=True, timeout=60)
            model_ok = model_proc.returncode == 0
            logger.info(f"Model {ticker}: {'OK' if model_ok else 'FAIL'}")

            # 3. KYC
            kyc_path = REPO_ROOT / "dashboard" / "data" / "kyc" / f"{ticker}.json"
            kyc_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bots" / "kyc_screen.py"),
                 "--ticker", ticker, "--output", str(kyc_path)],
                capture_output=True, text=True, timeout=30)
            kyc_ok = kyc_proc.returncode == 0
            logger.info(f"KYC {ticker}: {'OK' if kyc_ok else 'FAIL'}")

            # 4. Pitchbook
            pitch_path = REPO_ROOT / "dashboard" / "data" / "pitchbooks" / f"{ticker}.md"
            pitch_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bots" / "pitchbook_generator.py"),
                 "--ticker", ticker,
                 "--research", str(output_path), "--earnings", str(earn_path if earn_path.exists() else ""),
                 "--model", str(model_path if model_path.exists() else ""),
                 "--kyc", str(kyc_path if kyc_path.exists() else ""),
                 "--output", str(pitch_path)],
                capture_output=True, text=True, timeout=60)
            logger.info(f"Pitchbook {ticker}: {'OK' if pitch_proc.returncode == 0 else 'FAIL'}")

            # 5. Advisor reasoning
            reason_path = REPO_ROOT / "dashboard" / "data" / "advisor_notes" / f"{ticker}.json"
            reason_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bots" / "advisor_reasoning.py"),
                 "--research", str(output_path),
                 "--earnings", str(earn_path if earn_path.exists() else ""),
                 "--model", str(model_path if model_path.exists() else ""),
                 "--pitchbook", str(pitch_path),
                 "--output", str(reason_path)],
                capture_output=True, text=True, timeout=30)
            logger.info(f"Reasoning {ticker}: {'OK' if reason_proc.returncode == 0 else 'FAIL'}")

            # Load data for strategy routing
            earn_data = json.load(open(earn_path, "r")) if earn_path.exists() else {}
            model_data = json.load(open(model_path, "r")) if model_path.exists() else {}
            kyc_data = json.load(open(kyc_path, "r")) if kyc_path.exists() else {}

            strategy_label = "GROWTH"
            if model_data.get("margin_of_safety_pct", 0) > 15:
                strategy_label = "VALUE"
            elif earn_data.get("earnings_catalyst_score", 0) > 65:
                strategy_label = "MOMENTUM"
            elif conf > 75 and kyc_data.get("compliance_score", 100) > 80:
                strategy_label = "QUALITY"

            # 6. Position sizing
            pos_path = REPO_ROOT / "dashboard" / "data" / "portfolio_targets" / f"{ticker}.json"
            pos_path.parent.mkdir(parents=True, exist_ok=True)
            pos_proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bots" / "portfolio_constructor.py"),
                 "--ticker", ticker, "--confidence", str(conf),
                 "--margin_of_safety", str(model_data.get("margin_of_safety_pct", 10)),
                 "--strategy", strategy_label, "--output", str(pos_path)],
                capture_output=True, text=True, timeout=30)
            pos_ok = pos_proc.returncode == 0
            logger.info(f"Position {ticker}: {'OK' if pos_ok else 'FAIL'}")

            # 7. Council Meeting (new in v2)
            council_data = {}
            use_council = True  # default on; can be controlled per-task later
            if use_council and earn_ok and model_ok and pos_ok:
                try:
                    council_data = _run_council(ticker, result_data, earn_path, model_path, kyc_path, reason_path, pos_path)
                    if council_data:
                        c_rec = council_data.get("consensus", {}).get("recommendation", rec)
                        c_score = council_data.get("consensus", {}).get("confidence", conf)
                        c_verdict = council_data.get("consensus", {}).get("verdict", "")
                        boost = council_data.get("consensus", {}).get("position_size_boost_pct", 0)
                        # If council differs, note it in summary but keep paper_trade consistent
                        if c_rec != rec:
                            logger.info(f"Council override: {rec} -> {c_rec} for {ticker}")
                        extra["council_recommendation"] = c_rec
                        extra["council_confidence"] = c_score
                        extra["council_verdict"] = c_verdict
                        extra["council_path"] = str(Path(council_data.get("memo_path", "")).relative_to(REPO_ROOT)) if council_data.get("memo_path") else ""
                        council_summary = f"Council: {c_rec} ({c_score}% {c_verdict})"
                        if boost > 0:
                            council_summary += f" [+{int(boost*100)}% size]"
                        extra["summary"] = f"{rec} ({conf}%) — Strategy: {strategy_label}. {council_summary}"
                except Exception as c_err:
                    logger.warning(f"Council error for {ticker}: {c_err}")

            # 8. Paper trade
            from bots.paper_trade import auto_trade_from_result
            trade_res = auto_trade_from_result(result_data)
            logger.info(f"Paper trade {ticker}: {trade_res.get('status')} — {trade_res.get('message','')[:100]}")

            # 9. Strategy tracker
            from bots.strategy_tracker import record_trade
            record_trade(result_data, model_data, earn_data, strategy_label)

            extra["advisor_pitchbook"] = str(pitch_path.relative_to(REPO_ROOT))
            extra["advisor_reasoning"] = str(reason_path.relative_to(REPO_ROOT))

        except Exception as e:
            logger.warning(f"Advisor pipeline error for {task_id}: {e}")

        move_task(str(BOARD_PATH), task_id, "In Progress", "Done", extra_fields=extra)
        logger.info(f"Task {task_id} completed and archived")

    _generate_new_tasks(board)
    _git_push("orchestrator: cycle complete")
    logger.info("=== Cycle complete ===")


# ── Entry ───────────────────────────────────────────────────────────

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
            logger.warning("Another instance is already running. Skipping.")
    except ImportError:
        run_cycle()

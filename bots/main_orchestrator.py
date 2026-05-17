"""
bots/main_orchestrator.py
Stock Command Center — Head Manager (v3 Real Data)
Reads whiteboard, runs real market analysis, executes paper trades, archives results.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = REPO_ROOT / "whiteboard" / "kanban.md"
OUTPUT_DIR = REPO_ROOT / "dashboard" / "data" / "output"
LOG_DIR = REPO_ROOT / "logs"
LOCK_FILE = Path("/tmp/stock-cycle.lock")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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


# ── Research pipeline ──────────────────────────────────────────────

def run_researcher(task: dict) -> dict | None:
    task_id = task.get("task_id", "UNKNOWN")
    subject = task.get("subject", "")
    output_path = OUTPUT_DIR / f"{task_id}.json"

    logger.info(f"[{task_id}] Research: {subject}")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bots" / "researcher_bot.py"),
         "--task-id", task_id, "--subject", subject,
         "--output", str(output_path)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        logger.error(f"[{task_id}] researcher_bot failed: {proc.stderr[:300]}")
        return None
    if not output_path.exists():
        logger.error(f"[{task_id}] No output file")
        return None
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[{task_id}] JSON parse error: {e}")
        return None


def run_financial_model(ticker: str) -> dict | None:
    output_path = REPO_ROOT / "dashboard" / "data" / "models" / f"{ticker}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bots" / "financial_model.py"),
         "--ticker", ticker, "--output", str(output_path)],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode == 0 and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def run_earnings(ticker: str) -> dict | None:
    output_path = REPO_ROOT / "dashboard" / "data" / "earnings" / f"{ticker}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bots" / "earnings_analyzer.py"),
         "--ticker", ticker, "--output", str(output_path)],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode == 0 and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# ── Trade ──────────────────────────────────────────────────────────

def execute_trade(result: dict) -> dict:
    from bots.paper_trade import auto_trade_from_result
    return auto_trade_from_result(result)


# ── Task helpers ───────────────────────────────────────────────────

WATCHLIST = [
    # ETFs
    "SPY", "QQQ", "IWM", "VTI", "VOO", "VGT", "XLK", "XLF", "XLE", "XLI",
    "SCHG", "SPYG", "MTUM", "SPMO", "SCHK", "SPYM", "VOOG",
    # Mega-cap tech
    "NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "AMD", "AVGO", "CRM",
    # Large-cap
    "INTC", "ADBE", "NFLX", "PYPL", "UBER", "COIN", "PLTR",
    # Banks / Finance
    "JPM", "BAC", "GS", "WFC",
    # Energy / Industrials
    "XOM", "CVX", "BA", "F", "GE",
    # Healthcare
    "UNH", "JNJ", "LLY", "PFE",
    # Consumer
    "DIS", "NKE", "COST", "WMT", "HD", "LOW", "SBUX", "KO", "PEP",
    # Others
    "ARKK",
    # Crypto
    "BTC-USD", "ETH-USD", "SOL-USD",
]


def _generate_new_tasks(board: dict):
    done_tickers = set()
    for section in ["Done", "To Do", "In Progress"]:
        for t in board.get(section, []):
            subj = t.get("subject", "")
            m = __import__('re').search(r'\b([A-Z]{2,5}(?:-USD)?)\b', subj)
            if m:
                done_tickers.add(m.group(1))

    available = [t for t in WATCHLIST if t not in done_tickers]
    if len(available) < 5:
        available = WATCHLIST
    import random
    for ticker in available[:5]:
        is_crypto = "USD" in ticker
        add_task(
            path=str(BOARD_PATH),
            subject=f"{ticker} {'crypto momentum' if is_crypto else 'analysis'}",
            details=f"Real-time market analysis for {ticker}. Auto-generated watchlist task.",
            priority="medium",
            bot="researcher_bot",
            git_commit=True,
        )
        logger.info(f"Auto-added task: {ticker}")


# ── Main cycle ─────────────────────────────────────────────────────

def run_cycle():
    logger.info("=== Starting orchestrator cycle ===")
    ensure_all_bots_registered()
    _git_pull()

    board = load_board(str(BOARD_PATH))
    todo = board.get("To Do", [])

    if not todo:
        logger.info("No tasks. Auto-generating from watchlist.")
        _generate_new_tasks(board)
        _git_push("orchestrator: auto-generate watchlist tasks")
        return

    for task in todo[:5]:
        task_id = task.get("task_id", "UNKNOWN")
        now_iso = datetime.now(timezone.utc).isoformat()
        move_task(str(BOARD_PATH), task_id, "To Do", "In Progress",
                  extra_fields={"started_at": now_iso})

        result = run_researcher(task)
        if not result:
            move_task(str(BOARD_PATH), task_id, "In Progress", "To Do",
                      extra_fields={"summary": "FAILED — will retry next cycle"})
            logger.warning(f"[{task_id}] research failed, moved back to To Do")
            continue

        ticker = result.get("ticker", "")
        if not ticker:
            move_task(str(BOARD_PATH), task_id, "In Progress", "Done",
                      extra_fields={"summary": f"No ticker extracted — {result.get('summary', '')[:80]}"})
            continue

        # Record prediction
        try:
            record_prediction("researcher_bot", ticker,
                              result.get("recommendation", "HOLD"),
                              result.get("confidence", 0),
                              result.get("paper_trade_price", 0))
        except Exception as e:
            logger.warning(f"Registry error: {e}")

        # Run valuation + earnings in parallel (background-ish, we just run sequentially)
        try:
            model = run_financial_model(ticker)
            if model:
                result["model"] = {"blended_target": model.get("blended_target"),
                                   "margin_of_safety_pct": model.get("margin_of_safety_pct"),
                                   "verdict": model.get("verdict"),
                                   "upside_pct": model.get("upside_pct")}
        except Exception as e:
            logger.warning(f"Model error for {ticker}: {e}")

        try:
            earn = run_earnings(ticker)
            if earn:
                result["earnings"] = {"catalyst_score": earn.get("earnings_catalyst_score"),
                                      "verdict": earn.get("verdict"),
                                      "eps_trend": earn.get("eps_trend"),
                                      "next_earnings_date": earn.get("next_earnings_date")}
        except Exception as e:
            logger.warning(f"Earnings error for {ticker}: {e}")

        # Trade
        try:
            trade_res = execute_trade(result)
            logger.info(f"[{task_id}] Trade {ticker}: {trade_res.get('status')} — {trade_res.get('message', '')[:100]}")
            result["trade_result"] = trade_res
        except Exception as e:
            logger.warning(f"Trade error for {ticker}: {e}")

        # Save enriched result
        output_path = OUTPUT_DIR / f"{task_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        summary = result.get("summary", "")[:160]
        move_task(str(BOARD_PATH), task_id, "In Progress", "Done",
                  extra_fields={
                      "completed_at": datetime.now(timezone.utc).isoformat(),
                      "result": str(output_path.relative_to(REPO_ROOT)),
                      "summary": summary,
                  })
        logger.info(f"[{task_id}] Done: {summary}")

    _generate_new_tasks(board)
    _git_push("orchestrator: cycle complete with real data")
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
            logger.warning("Another instance is already running. Skipping.")
    except ImportError:
        run_cycle()

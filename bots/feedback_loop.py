"""
bots/feedback_loop.py
After positions close or after a delay, compare predictions against actual outcomes.
Updates bot_registry.json and auto-generates whiteboard improvement tasks.
Usage:
  python bots/feedback_loop.py evaluate --age-days 5
  python bots/feedback_loop.py generate-tasks
  python bots/feedback_loop.py report
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS_PATH = REPO_ROOT / "dashboard" / "data" / "prediction_ledger.json"
STRATEGIES_PATH = REPO_ROOT / "dashboard" / "data" / "strategies" / "ledger.json"
LEDGER_PATH = REPO_ROOT / "dashboard" / "data" / "paper_ledger.json"
REGISTRY_PATH = REPO_ROOT / "dashboard" / "data" / "bot_registry.json"
BOARD_PATH = REPO_ROOT / "whiteboard" / "kanban.md"
FEEDBACK_PATH = REPO_ROOT / "dashboard" / "data" / "feedback_report.json"

sys.path.insert(0, str(REPO_ROOT))
from whiteboard.parser import add_task


# ── Config ─────────────────────────────────────────────────────────

ACCURACY_BOT_THRESHOLD = 40.0   # below this → improvement task
WIN_RATE_STRATEGY_THRESHOLD = 45.0
gLOBAL_ACCURACY_WINDOW = 20     # last N predictions per bot
FEEDBACK_AGE_DAYS = 5


# ── Load helpers ───────────────────────────────────────────────────

def _load(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Accuracy evaluation ─────────────────────────────────────────────

def _was_prediction_correct(pred: dict, trade: dict) -> bool:
    """
    A prediction is correct if the recommendation direction (BUY/ACCUMULATE vs SELL/HOLD)
    matched the actual trade outcome.
    - BUY/ACCUMULATE → correct if return_pct > 0
    - SELL   (which means close/sell) → correct if return_pct <= 0  (we predicted it would go down)
    - HOLD/WATCH → correct if abs(return_pct) < 3% (flat)
    """
    rec = pred.get("recommendation", "HOLD").upper()
    roi = trade.get("return_pct", 0)

    if rec in ("BUY", "ACCUMULATE"):
        return roi > 0
    elif rec == "SELL":
        return roi <= 0
    else:
        return abs(roi) < 3.0


def evaluate_predictions(age_days: int = FEEDBACK_AGE_DAYS):
    """
    Walk through closed trades in the paper ledger.
    For each trade, find matching predictions and mark outcomes.
    """
    ledger = _load(LEDGER_PATH)
    preds = _load(PREDICTIONS_PATH)
    registry = _load(REGISTRY_PATH)

    if not ledger.get("history"):
        print("No closed trades yet. Nothing to evaluate.")
        return []

    evaluated = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=age_days)

    for trade in ledger["history"]:
        closed_at = trade.get("closed_at", "")
        try:
            closed_dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
        except Exception:
            continue
        if closed_dt < cutoff:
            continue

        ticker = trade.get("ticker", "")
        if not ticker:
            continue

        # Find un-evaluated predictions for this ticker
        for p in preds.get("predictions", []):
            if p.get("evaluated", False):
                continue
            if p.get("ticker", "").upper() == ticker.upper():
                correct = _was_prediction_correct(p, trade)
                p["evaluated"] = True
                p["was_correct"] = correct
                p["roi_at_eval"] = trade.get("return_pct", 0)
                p["evaluated_at"] = datetime.now(timezone.utc).isoformat()

                # Update bot registry
                bot_name = p.get("bot", "unknown")
                bot = registry.setdefault("bots", {}).get(bot_name)
                if bot is None:
                    # Register on the fly
                    registry["bots"][bot_name] = {
                        "name": bot_name,
                        "expertise": "auto",
                        "historical_accuracy": 50.0,
                        "total_predictions": 0,
                        "correct_predictions": 0,
                    }
                    bot = registry["bots"][bot_name]
                bot["total_predictions"] = bot.get("total_predictions", 0) + 1
                if correct:
                    bot["correct_predictions"] = bot.get("correct_predictions", 0) + 1
                total = bot["total_predictions"]
                bot["historical_accuracy"] = round(bot["correct_predictions"] / total * 100, 1) if total else 50.0
                bot["last_evaluated"] = datetime.now(timezone.utc).isoformat()

                evaluated.append({
                    "bot": bot_name,
                    "ticker": ticker,
                    "recommendation": p["recommendation"],
                    "correct": correct,
                    "roi_pct": trade.get("return_pct", 0),
                })

    _save(PREDICTIONS_PATH, preds)
    _save(REGISTRY_PATH, registry)

    print(f"Evaluated {len(evaluated)} predictions against actual outcomes.")
    return evaluated


# ── Strategy win rate ────────────────────────────────────────────────

def evaluate_strategies() -> dict:
    strategies_data = _load(STRATEGIES_PATH)
    if not strategies_data.get("trades"):
        return {}

    strategy_map = {}
    for t in strategies_data["trades"]:
        s = t.get("strategy", "UNKNOWN")
        if s not in strategy_map:
            strategy_map[s] = {"wins": 0, "losses": 0, "total": 0, "returns": []}
        strategy_map[s]["total"] += 1
        ret = t.get("return_pct", None)
        if ret is not None:
            strategy_map[s]["returns"].append(ret)
            if ret > 0:
                strategy_map[s]["wins"] += 1
            else:
                strategy_map[s]["losses"] += 1

    stats = {}
    for s, counts in strategy_map.items():
        total = counts["total"]
        wins = counts["wins"]
        avg = sum(counts["returns"]) / total if total else 0
        stats[s] = {
            "trades": total,
            "win_rate": round(wins / total * 100, 1) if total else 0,
            "avg_return_pct": round(avg, 2),
            "wins": wins,
            "losses": counts["losses"],
        }
    return stats


# ── Auto-task generation ────────────────────────────────────────────

def generate_improvement_tasks():
    registry = _load(REGISTRY_PATH)
    strategy_stats = evaluate_strategies()
    tasks_created = []

    # Check bots that need improvement
    for bot_name, bot in registry.get("bots", {}).items():
        if bot_name == "unknown":
            continue
        total = bot.get("total_predictions", 0)
        if total < 5:
            continue
        acc = bot.get("historical_accuracy", 100.0)
        if acc < ACCURACY_BOT_THRESHOLD:
            details = f"- Bot: {bot_name}\n- Accuracy: {acc}% over last {total} predictions\n- Target: improve to >= {ACCURACY_BOT_THRESHOLD}%\n- Suggestion: review data sources and scoring weights\n- Created via feedback_loop auto-improve"
            add_task(
                path=str(BOARD_PATH),
                subject=f"Auto: Improve {bot_name} model",
                details=details,
                priority="high",
                bot="self_build",
            )
            tasks_created.append(f"Improve {bot_name} ({acc}%)")

    # Check strategies that need tuning
    for strat, stats in strategy_stats.items():
        wr = stats.get("win_rate", 100.0)
        total = stats.get("trades", 0)
        if total < 5:
            continue
        if wr < WIN_RATE_STRATEGY_THRESHOLD:
            details = f"- Strategy: {strat}\n- Win rate: {wr}% over {total} trades\n- Target: improve to >= {WIN_RATE_STRATEGY_THRESHOLD}%\n- Suggestion: adjust entry/exit thresholds or combine with another strategy\n- Created via feedback_loop auto-improve"
            add_task(
                path=str(BOARD_PATH),
                subject=f"Auto: Tune {strat} strategy parameters",
                details=details,
                priority="high",
                bot="self_build",
            )
            tasks_created.append(f"Tune {strat} ({wr}%)")

    print(f"Auto-generated {len(tasks_created)} improvement tasks.")
    return tasks_created


# ── Feedback report ────────────────────────────────────────────────

def generate_report() -> dict:
    registry = _load(REGISTRY_PATH)
    strategy_stats = evaluate_strategies()
    ledger = _load(LEDGER_PATH)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": {
            "closed_trades": len(ledger.get("history", [])),
            "open_positions": len(ledger.get("positions", {})),
            "cash": ledger.get("cash", 0),
        },
        "bot_leaderboard": [],
        "strategy_stats": strategy_stats,
        "warnings": [],
    }

    # Build leaderboard
    bots = list(registry.get("bots", {}).values())
    bots.sort(key=lambda b: b.get("historical_accuracy", 0), reverse=True)
    for b in bots:
        total = b.get("total_predictions", 0)
        report["bot_leaderboard"].append({
            "name": b["name"],
            "expertise": b.get("expertise", ""),
            "accuracy": b.get("historical_accuracy", 0),
            "predictions": total,
            "correct": b.get("correct_predictions", 0),
        })
        # Warnings for poor performers
        if total >= 5 and b.get("historical_accuracy", 100) < ACCURACY_BOT_THRESHOLD:
            report["warnings"].append(f"{b['name']} accuracy {b['historical_accuracy']}% — below threshold")

    # Strategy warnings
    for s, stats in strategy_stats.items():
        if stats.get("trades", 0) >= 5 and stats.get("win_rate", 100) < WIN_RATE_STRATEGY_THRESHOLD:
            report["warnings"].append(f"Strategy {s} win rate {stats['win_rate']}% — below threshold")

    _save(FEEDBACK_PATH, report)
    print(f"Feedback report saved to {FEEDBACK_PATH}")
    return report


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Feedback Loop — evaluate predictions and generate improvement tasks")
    sub = parser.add_subparsers(dest="cmd")

    p_eval = sub.add_parser("evaluate", help="Score predictions against closed trades")
    p_eval.add_argument("--age-days", type=int, default=FEEDBACK_AGE_DAYS)

    sub.add_parser("generate-tasks", help="Auto-generate whiteboard improvement tasks")
    sub.add_parser("report", help="Generate feedback report JSON")

    args = parser.parse_args()

    if args.cmd == "evaluate":
        evaluate_predictions(args.age_days)
    elif args.cmd == "generate-tasks":
        generate_improvement_tasks()
    elif args.cmd == "report":
        generate_report()
    else:
        evaluate_predictions()
        generate_improvement_tasks()
        generate_report()


if __name__ == "__main__":
    main()

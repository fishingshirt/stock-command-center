"""
bots/bot_registry.py
Shared registry for all specialist bots: identity, expertise, and historical accuracy tracking.
Usage:
  python bots/bot_registry.py register --name "earnings_analyzer" --expertise "earnings_surprise"
  python bots/bot_registry.py predict --name "earnings_analyzer" --ticker "NVDA" --recommendation "BUY" --confidence 82
  python bots/bot_registry.py outcome --name "earnings_analyzer" --ticker "NVDA" --was_correct true
  python bots/bot_registry.py leaderboard
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "dashboard" / "data" / "bot_registry.json"

# ── Persistence ──────────────────────────────────────────────────

def _load_registry() -> dict:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        return {"bots": {}, "updated_at": datetime.now(timezone.utc).isoformat()}
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(registry: dict):
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


# ── Core API ─────────────────────────────────────────────────────

def register_bot(name: str, expertise: str = "general"):
    registry = _load_registry()
    if name not in registry["bots"]:
        registry["bots"][name] = {
            "name": name,
            "expertise": expertise,
            "historical_accuracy": 50.0,
            "total_predictions": 0,
            "correct_predictions": 0,
            "last_run": None,
            "avg_confidence": 65.0,
            "confidence_history": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_registry(registry)
        print(f"Registered new bot: {name} ({expertise})")
    else:
        print(f"Bot already registered: {name}")
    return registry["bots"][name]


def record_prediction(name: str, ticker: str, recommendation: str, confidence: int, price_at_predict: float = 0.0):
    registry = _load_registry()
    bot = registry["bots"].get(name)
    if not bot:
        print(f"WARN: {name} not in registry, auto-registering")
        bot = register_bot(name, expertise="general")

    bot["total_predictions"] += 1
    bot["last_run"] = datetime.now(timezone.utc).isoformat()
    bot["confidence_history"] = bot.get("confidence_history", []) + [confidence]
    bot["confidence_history"] = bot["confidence_history"][-30:]
    bot["avg_confidence"] = round(sum(bot["confidence_history"]) / len(bot["confidence_history"]), 1)

    # Append to predictions ledger
    preds_path = REPO_ROOT / "dashboard" / "data" / "prediction_ledger.json"
    preds_path.parent.mkdir(parents=True, exist_ok=True)
    preds = {"predictions": []}
    if preds_path.exists():
        try:
            with open(preds_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and "predictions" in loaded:
                preds = loaded
        except Exception:
            pass
    preds["predictions"].append({
        "bot": name,
        "ticker": ticker.upper(),
        "recommendation": recommendation,
        "confidence": confidence,
        "price_at_predict": price_at_predict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluated": False,
        "was_correct": None,
        "roi_at_eval": None,
    })
    with open(preds_path, "w", encoding="utf-8") as f:
        json.dump(preds, f, indent=2)

    _save_registry(registry)
    print(f"{name} predicted {ticker}={recommendation} ({confidence}%)")


def record_outcome(name: str, ticker: str, was_correct: bool, roi_pct: float = 0.0):
    registry = _load_registry()
    bot = registry["bots"].get(name)
    if not bot:
        print(f"ERROR: {name} not found in registry")
        return False

    if was_correct:
        bot["correct_predictions"] += 1

    total = bot["total_predictions"]
    bot["historical_accuracy"] = round(bot["correct_predictions"] / total * 100, 1) if total > 0 else 50.0
    _save_registry(registry)
    print(f"{name} outcome recorded for {ticker}: correct={was_correct} (accuracy {bot['historical_accuracy']}%)")

    # Mark prediction as evaluated
    preds_path = REPO_ROOT / "dashboard" / "data" / "prediction_ledger.json"
    if preds_path.exists():
        preds = _load_json(preds_path)
        for p in preds.get("predictions", [])[::-1]:
            if p["bot"] == name and p["ticker"] == ticker.upper() and not p.get("evaluated", False):
                p["evaluated"] = True
                p["was_correct"] = was_correct
                p["roi_at_eval"] = roi_pct
                _save_json(preds_path, preds)
                break
    return True


def get_bot_stats(name: str) -> dict:
    registry = _load_registry()
    bot = registry["bots"].get(name)
    if not bot:
        return {"error": f"Bot {name} not found"}
    return bot


def get_leaderboard() -> list:
    registry = _load_registry()
    bots = list(registry["bots"].values())
    # Sort by historical_accuracy desc, then by total_predictions desc
    bots.sort(key=lambda b: (b.get("historical_accuracy", 50.0), b.get("total_predictions", 0)), reverse=True)
    return [
        {
            "rank": i + 1,
            "name": b["name"],
            "expertise": b["expertise"],
            "accuracy": b["historical_accuracy"],
            "predictions": b["total_predictions"],
            "correct": b["correct_predictions"],
            "avg_confidence": b["avg_confidence"],
            "last_run": b["last_run"],
        }
        for i, b in enumerate(bots)
    ]


def ensure_all_bots_registered():
    """Idempotently register all known specialist bots."""
    known = [
        ("researcher_bot", "multi-domain_research"),
        ("earnings_analyzer", "earnings_surprise"),
        ("financial_model", "dcf_valuation"),
        ("kyc_screen", "compliance_risk"),
        ("pitchbook_generator", "investment_memo"),
        ("advisor_reasoning", "strategy_rationale"),
        ("portfolio_constructor", "position_sizing"),
    ]
    for name, expertise in known:
        register_bot(name, expertise)


# ── Helpers ──────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bot Registry")
    sub = parser.add_subparsers(dest="cmd")

    p_reg = sub.add_parser("register", help="Register a bot")
    p_reg.add_argument("--name", required=True)
    p_reg.add_argument("--expertise", default="general")

    p_pred = sub.add_parser("predict", help="Record a prediction")
    p_pred.add_argument("--name", required=True)
    p_pred.add_argument("--ticker", required=True)
    p_pred.add_argument("--recommendation", required=True)
    p_pred.add_argument("--confidence", type=int, required=True)
    p_pred.add_argument("--price", type=float, default=0.0)

    p_out = sub.add_parser("outcome", help="Record if prediction was correct")
    p_out.add_argument("--name", required=True)
    p_out.add_argument("--ticker", required=True)
    p_out.add_argument("--was_correct", type=lambda x: x.lower() == "true", required=True)
    p_out.add_argument("--roi_pct", type=float, default=0.0)

    sub.add_parser("leaderboard", help="Show accuracy leaderboard")
    sub.add_parser("ensure_all", help="Register all known bots")

    args = parser.parse_args()

    if args.cmd == "register":
        register_bot(args.name, args.expertise)
    elif args.cmd == "predict":
        record_prediction(args.name, args.ticker, args.recommendation, args.confidence, args.price)
    elif args.cmd == "outcome":
        record_outcome(args.name, args.ticker, args.was_correct, args.roi_pct)
    elif args.cmd == "leaderboard":
        print(json.dumps(get_leaderboard(), indent=2))
    elif args.cmd == "ensure_all":
        ensure_all_bots_registered()
        print(json.dumps(get_leaderboard(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

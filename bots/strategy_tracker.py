"""
bots/strategy_tracker.py
Tags trades with strategy and tracks performance per strategy.
Usage: called by orchestrator after each completed research task.
"""
import json, random
from datetime import datetime, timezone
from pathlib import Path

STRATEGIES = ["MOMENTUM", "VALUE", "GROWTH", "QUALITY", "INCOME"]

def classify_strategy(research: dict, model: dict, earnings: dict) -> str:
    """Classify recommendation into strategy bucket."""
    conf = research.get("confidence", 50)
    mos = model.get("margin_of_safety_pct", 0)
    e_score = earnings.get("earnings_catalyst_score", 0)
    rec = research.get("recommendation", "HOLD")
    
    if e_score > 65 and conf > 70:
        return "MOMENTUM"
    elif mos > 15 and conf > 60:
        return "VALUE"
    elif rec in ("BUY", "ACCUMULATE") and e_score > 40 and conf > 65:
        return "GROWTH"
    elif conf > 75 and mos > 10:
        return "QUALITY"
    elif rec == "HOLD" and conf < 60:
        return "INCOME"
    else:
        return random.choice(STRATEGIES)


def record_trade(research: dict, model: dict, earnings: dict, strategy: str, ledger: dict = None):
    """Record a trade into strategy tracking."""
    ticker = _extract_ticker(research.get("subject", ""))
    trade = {
        "ticker": ticker,
        "strategy": strategy,
        "recommendation": research.get("recommendation", "HOLD"),
        "confidence": research.get("confidence", 0),
        "entry_price": research.get("paper_trade_price", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "margin_of_safety": model.get("margin_of_safety_pct", 0),
        "earnings_catalyst": earnings.get("earnings_catalyst_score", 0),
        "open": True,
        "exit_price": None,
        "return_pct": None,
        "model_target": model.get("blended_target", 0),
    }
    
    tracking_file = Path("dashboard/data/strategies/ledger.json")
    tracking_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {"trades": [], "updated_at": datetime.now(timezone.utc).isoformat()}
    if tracking_file.exists():
        try:
            with open(tracking_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    
    data["trades"].append(trade)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalc stats per strategy
    stats = {}
    for s in STRATEGIES:
        st = [t for t in data["trades"] if t["strategy"] == s and t.get("return_pct") is not None]
        if st:
            wins = sum(1 for t in st if t["return_pct"] > 0)
            total = len(st)
            avg_ret = sum(t["return_pct"] for t in st) / total
            stats[s] = {
                "trades": total,
                "win_rate": round(wins / total * 100, 1),
                "avg_return_pct": round(avg_ret, 2),
                "best_trade": round(max(t["return_pct"] for t in st), 2),
                "worst_trade": round(min(t["return_pct"] for t in st), 2),
            }
    data["strategy_stats"] = stats
    
    with open(tracking_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    return trade


def _extract_ticker(subject: str) -> str:
    import re
    m = re.search(r'\b([A-Z]{2,5})\b', subject)
    return m.group(1) if m else ""


def get_leaderboard() -> dict:
    """Get strategy performance board."""
    tracking_file = Path("dashboard/data/strategies/ledger.json")
    if not tracking_file.exists():
        return {"strategies": [], "message": "No trades recorded yet"}
    with open(tracking_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("strategy_stats", {})


if __name__ == "__main__":
    import sys
    print(json.dumps(get_leaderboard(), indent=2))
    sys.exit(0)

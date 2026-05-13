"""
bots/portfolio_constructor.py
Position sizing, sector limits, Kelly criterion, diversification.
Usage: called after advisor reasoning to size the position.
"""
import argparse, json, random, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def load_ledger() -> dict:
    p = Path("dashboard/data/paper_ledger.json")
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cash": 100000.0, "positions": {}}


def get_sector_concentration(ledger: dict) -> dict:
    """Mock sector allocation from positions."""
    sectors = {"Technology": 0, "Healthcare": 0, "Energy": 0, "Finance": 0, "Consumer": 0, "Other": 0}
    for pos in ledger.get("positions", {}).values():
        ticker = pos.get("ticker", "")
        value = pos.get("last_price", pos.get("entry_price", 0)) * pos.get("shares", 0)
        if ticker in ("NVDA", "AAPL", "MSFT", "AMD", "INTC"):
            sectors["Technology"] += value
        elif ticker in ("JNJ", "PFE", "UNH"):
            sectors["Healthcare"] += value
        elif ticker in ("XOM", "CVX"):
            sectors["Energy"] += value
        elif ticker in ("JPM", "GS", "BAC"):
            sectors["Finance"] += value
        elif ticker in ("AMZN", "DIS", "KO"):
            sectors["Consumer"] += value
        else:
            sectors["Other"] += value
    return sectors


def kelly_criterion(win_rate: float, avg_win_pct: float, avg_loss_pct: float) -> float:
    """Kelly fraction: f* = W - (1-W)/R."""
    if avg_loss_pct <= 0:
        return 0.05  # default if no losses yet
    R = avg_win_pct / avg_loss_pct
    kelly = win_rate - (1 - win_rate) / R if R > 0 else 0
    return max(0.02, min(0.25, kelly))  # cap between 2% and 25%


def recommend_position(ticker: str, confidence: float, margin_of_safety: float, strategy: str) -> dict:
    ledger = load_ledger()
    cash = ledger.get("cash", 100000.0)
    total_value = cash + sum(
        p.get("last_price", p.get("entry_price", 0)) * p.get("shares", 0)
        for p in ledger.get("positions", {}).values()
    )
    
    # Base sizing
    base_pct = 0.10  # 10% baseline
    
    # Kelly adjustment
    win_rate = random.uniform(0.55, 0.75)  # mock from strategy history
    kelly = kelly_criterion(win_rate, 0.05, 0.03)  # ~5% avg win, ~3% avg loss
    
    # Adjust for margin of safety
    mos_mult = 1.0 + (margin_of_safety / 100) * 2  # more MoS = bigger position
    
    # Adjust for confidence
    conf_mult = confidence / 100  # linear scaling
    
    target_pct = base_pct * kelly * 2 * mos_mult * conf_mult  # *2 because half kelly is common
    target_pct = max(0.02, min(0.25, target_pct))
    
    target_dollars = total_value * target_pct
    
    # Sector limit check
    sectors = get_sector_concentration(ledger)
    ticker_sector = "Technology" if ticker in ("NVDA", "AAPL", "MSFT") else "Other"
    current_sector_pct = sectors.get(ticker_sector, 0) / total_value if total_value > 0 else 0
    
    sector_limit_msg = None
    if current_sector_pct + target_pct > 0.30:
        sector_limit_msg = f"Sector limit: would exceed 30% {ticker_sector}"
        target_pct = max(0.02, 0.30 - current_sector_pct)
        target_dollars = total_value * target_pct
    
    # Diversification: limit max position
    if target_pct > 0.20:
        target_pct = 0.20
        target_dollars = total_value * target_pct
    
    return {
        "ticker": ticker,
        "target_pct_of_portfolio": round(target_pct * 100, 2),
        "target_dollars": round(target_dollars, 2),
        "kelly_fraction": round(kelly, 3),
        "confidence_multiplier": round(conf_mult, 2),
        "margin_of_safety_multiplier": round(mos_mult, 2),
        "diversification_limit": "20% max single position",
        "sector_risk": sector_limit_msg or "Within limits",
        "cash_available": round(cash, 2),
        "total_portfolio_value": round(total_value, 2),
        "strategy": strategy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run(args) -> bool:
    rec = recommend_position(args.ticker, args.confidence, args.margin_of_safety, args.strategy)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print(f"Position for {args.ticker}: {rec['target_pct_of_portfolio']}% = ${rec['target_dollars']} | Sector: {rec['sector_risk']}")
    return True


if __name__ == "__main__":
    import sys
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--confidence", type=float, default=65.0)
    p.add_argument("--margin_of_safety", type=float, default=10.0)
    p.add_argument("--strategy", default="GROWTH")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

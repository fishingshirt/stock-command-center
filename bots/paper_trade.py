"""
bots/paper_trade.py
Paper trading engine. Treats virtual positions as real money for learning.
Trades ONLY during US market hours (9:30-16:00 ET, Mon-Fri).
"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "dashboard" / "data" / "paper_ledger.json"
SETTINGS_PATH = REPO_ROOT / "dashboard" / "data" / "settings.json"

LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)

INITIAL_CAPITAL = 100000.0


def _is_market_open() -> dict:
    """Check if US stock market is currently open."""
    now = datetime.now(timezone.utc)
    et_offset = timedelta(hours=-4)  # DST
    et_now = now + et_offset
    weekday = et_now.weekday()
    if weekday >= 5:
        return {"open": False, "reason": f"Weekend ({et_now.strftime('%A')})", "et_time": et_now.strftime("%H:%M")}
    hour = et_now.hour
    minute = et_now.minute
    current = hour * 60 + minute
    market_open = 9 * 60 + 30
    market_close = 16 * 60
    if current < market_open:
        return {"open": False, "reason": "Pre-market", "et_time": et_now.strftime("%H:%M")}
    if current > market_close:
        return {"open": False, "reason": "After-hours", "et_time": et_now.strftime("%H:%M")}
    return {"open": True, "reason": "Regular hours", "et_time": et_now.strftime("%H:%M")}


def _load_settings() -> dict:
    defaults = {
        "auto_trade_enabled": False,
        "paper_trade_confidence_threshold": 70,
        "max_positions": 10,
        "position_size_pct": 0.10,
        "initial_capital": 100000.0,
    }
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            defaults.update(loaded)
        except Exception:
            pass
    return defaults


def _save_settings(settings: dict):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def _load_ledger() -> dict:
    if not LEDGER_PATH.exists():
        return {
            "cash": INITIAL_CAPITAL,
            "initial_capital": INITIAL_CAPITAL,
            "positions": {},
            "history": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_ledger(ledger: dict):
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)


def get_stats() -> dict:
    ledger = _load_ledger()
    positions = ledger.get("positions", {})
    history = ledger.get("history", [])
    
    # Update prices for open positions
    try:
        import yfinance as yf_local
        for ticker in positions:
            try:
                t = yf_local.Ticker(ticker)
                hist = t.history(period="1d")
                if len(hist) > 0:
                    positions[ticker]["last_price"] = round(float(hist.Close.iloc[-1]), 4)
            except Exception:
                pass
        _save_ledger(ledger)
    except Exception:
        pass

    realized_pnl = sum(h.get("pnl", 0) for h in history)
    unrealized_pnl = sum(
        (pos.get("last_price", pos["entry_price"]) - pos["entry_price"]) * pos["shares"]
        for pos in positions.values()
    )
    total_value = ledger["cash"] + sum(
        pos.get("last_price", pos["entry_price"]) * pos["shares"]
        for pos in positions.values()
    )

    wins = [h for h in history if h.get("pnl", 0) > 0]
    losses = [h for h in history if h.get("pnl", 0) < 0]

    win_rate = len(wins) / len(history) * 100 if history else 0
    avg_return = sum(h.get("return_pct", 0) for h in history) / len(history) if history else 0
    max_drawdown = min((h.get("return_pct", 0) for h in history), default=0)

    market_status = _is_market_open()

    return {
        "cash": round(ledger["cash"], 2),
        "total_value": round(total_value, 2),
        "total_return_pct": round((total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "open_positions_count": len(positions),
        "closed_trades_count": len(history),
        "win_rate": round(win_rate, 2),
        "avg_return_pct": round(avg_return, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "positions": positions,
        "history": history[-20:],
        "market_status": market_status,
        "initial_capital": INITIAL_CAPITAL,
    }


def buy(ticker: str, price: float, confidence: float, reasoning: str, shares: float = None, task_id: str = ""):
    """Open a paper position — only if market is open."""
    market = _is_market_open()
    if not market["open"]:
        return {"status": "market_closed", "message": f"Cannot buy — {market['reason']} ({market['et_time']} ET)", "market": market}
    
    ledger = _load_ledger()
    if ticker.upper() in ledger.get("positions", {}):
        return {"status": "already_open", "message": f"Position already open for {ticker}"}

    settings = _load_settings()
    position_size_pct = settings.get("position_size_pct", 0.10)
    max_positions = settings.get("max_positions", 10)
    
    if len(ledger.get("positions", {})) >= max_positions:
        return {"status": "max_positions", "message": f"Max {max_positions} positions reached"}

    if shares is None:
        invest = ledger["cash"] * position_size_pct
        shares = round(invest / price, 4)

    cost = shares * price
    if cost > ledger["cash"]:
        return {"status": "insufficient_funds", "message": f"Need ${cost:.2f}, have ${ledger['cash']:.2f}"}

    ledger["cash"] -= cost
    ledger["positions"][ticker.upper()] = {
        "ticker": ticker.upper(),
        "shares": shares,
        "entry_price": round(price, 4),
        "last_price": round(price, 4),
        "confidence": confidence,
        "reasoning": reasoning,
        "task_id": task_id,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_ledger(ledger)
    return {"status": "ok", "message": f"Bought {shares} {ticker} @ ${price}", "cost": round(cost, 2), "market": market}


def sell(ticker: str, price: float, reasoning: str = "", task_id: str = ""):
    """Close a paper position — only if market is open."""
    market = _is_market_open()
    if not market["open"]:
        return {"status": "market_closed", "message": f"Cannot sell — {market['reason']} ({market['et_time']} ET)", "market": market}
    
    ledger = _load_ledger()
    pos = ledger.get("positions", {}).pop(ticker.upper(), None)
    if not pos:
        return {"status": "no_position", "message": f"No open position for {ticker}"}

    proceeds = pos["shares"] * price
    pnl = proceeds - (pos["shares"] * pos["entry_price"])
    return_pct = (price - pos["entry_price"]) / pos["entry_price"] * 100
    hold_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(pos["opened_at"])).total_seconds()

    ledger["cash"] += proceeds
    ledger["history"].append({
        "ticker": ticker.upper(),
        "action": "SELL",
        "shares": pos["shares"],
        "entry_price": pos["entry_price"],
        "exit_price": round(price, 4),
        "pnl": round(pnl, 2),
        "return_pct": round(return_pct, 2),
        "hold_seconds": round(hold_seconds, 1),
        "reasoning": reasoning or pos.get("reasoning", ""),
        "opened_at": pos["opened_at"],
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id or pos.get("task_id", ""),
    })
    _save_ledger(ledger)
    return {
        "status": "ok",
        "message": f"Sold {pos['shares']} {ticker} @ ${price}",
        "pnl": round(pnl, 2),
        "return_pct": round(return_pct, 2),
        "market": market,
    }


def update_price(ticker: str, current_price: float):
    ledger = _load_ledger()
    pos = ledger.get("positions", {}).get(ticker.upper())
    if pos:
        pos["last_price"] = round(current_price, 4)
        _save_ledger(ledger)


def auto_trade_from_result(result: dict):
    """Auto-trade if confidence exceeds threshold and market is open."""
    settings = _load_settings()
    if not settings.get("auto_trade_enabled", False):
        return {"status": "skipped", "reason": "auto_trade_enabled=false"}

    rec = result.get("recommendation", "WATCH")
    conf = result.get("confidence", 0)
    ticker = result.get("key_metrics", {}).get("ticker") or _extract_ticker(result.get("subject", ""))
    price = result.get("key_metrics", {}).get("current_price") or result.get("paper_trade_price", 0)
    if price is None:
        price = 0
    task_id = result.get("task_id", "")
    summary = result.get("summary", "")

    threshold = settings.get("paper_trade_confidence_threshold", 70)
    max_positions = settings.get("max_positions", 10)

    if not ticker or not price:
        return {"status": "skipped", "reason": "missing ticker or price"}

    if rec in ("BUY", "ACCUMULATE"):
        ledger = _load_ledger()
        if len(ledger.get("positions", {})) >= max_positions:
            return {"status": "skipped", "reason": f"max_positions={max_positions} reached"}

    if rec in ("BUY", "ACCUMULATE") and conf >= threshold:
        return buy(ticker, price, conf, summary, task_id=task_id)
    elif rec == "SELL":
        return sell(ticker, price, summary, task_id=task_id)
    else:
        return {"status": "skipped", "reason": f"rec={rec} conf={conf} threshold={threshold}"}


def _extract_ticker(subject: str) -> str:
    import re
    m = re.search(r'\b([A-Z]{2,5})\b', subject)
    return m.group(1) if m else ""


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    elif cmd == "buy" and len(sys.argv) >= 4:
        print(json.dumps(buy(sys.argv[2], float(sys.argv[3]), 80.0, "manual buy"), indent=2))
    elif cmd == "sell" and len(sys.argv) >= 4:
        print(json.dumps(sell(sys.argv[2], float(sys.argv[3])), indent=2))
    else:
        print("Usage: python paper_trade.py [stats|buy TICKER PRICE|sell TICKER PRICE]")

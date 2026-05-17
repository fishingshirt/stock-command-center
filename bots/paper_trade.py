"""
bots/paper_trade.py
Paper trading engine. Actually buys AND sells. Rotates positions.
Conviction-scaled position sizing.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "dashboard" / "data" / "paper_ledger.json"
SETTINGS_PATH = REPO_ROOT / "dashboard" / "data" / "settings.json"
LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)

INITIAL_CAPITAL = 100000.0


def _load_settings() -> dict:
    defaults = {
        "auto_trade_enabled": True,
        "paper_trade_confidence_threshold": 60,
        "max_positions": 12,
        "position_size_pct": 0.08,
        "conviction_scaling": True,
        "enable_rotation": True,
        "rotation_threshold_diff": 15,
        "initial_capital": INITIAL_CAPITAL,
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


def _update_prices(ledger: dict):
    """Pull live prices for all open positions."""
    try:
        import yfinance as yf
        for ticker in list(ledger.get("positions", {}).keys()):
            try:
                t = yf.Ticker(ticker)
                # Use 5d instead of 1d to handle weekends/holidays
                hist = t.history(period="5d")
                if len(hist) > 0:
                    ledger["positions"][ticker]["last_price"] = round(float(hist.Close.iloc[-1]), 4)
            except Exception:
                pass
    except Exception:
        pass
    return ledger


def get_stats() -> dict:
    ledger = _load_ledger()
    positions = ledger.get("positions", {})
    history = ledger.get("history", [])
    ledger = _update_prices(ledger)
    _save_ledger(ledger)

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

    win_rate = round(len(wins) / len(history) * 100, 2) if history else 0
    avg_return = round(sum(h.get("return_pct", 0) for h in history) / len(history), 2) if history else 0
    max_dd = round(min((h.get("return_pct", 0) for h in history), default=0), 2)

    return {
        "cash": round(ledger["cash"], 2),
        "total_value": round(total_value, 2),
        "total_return_pct": round((total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "open_positions_count": len(positions),
        "closed_trades_count": len(history),
        "win_rate": win_rate,
        "avg_return_pct": avg_return,
        "max_drawdown_pct": max_dd,
        "positions": positions,
        "history": history[-20:],
        "initial_capital": INITIAL_CAPITAL,
        "settings": _load_settings(),
    }


def _calc_position_size(cash: float, confidence: float, base_pct: float, conviction_scaling: bool) -> float:
    """Conviction-scaled position size."""
    if not conviction_scaling:
        return cash * base_pct
    # Scale from 4% at 60% confidence to 12% at 95% confidence
    pct = 0.04 + (confidence - 60) / 35 * 0.08 if confidence >= 60 else 0.04
    pct = max(0.04, min(0.12, pct))
    return cash * pct


def buy(ticker: str, price: float, confidence: float, reasoning: str, shares: float = None, task_id: str = ""):
    ledger = _load_ledger()
    ticker = ticker.upper()
    if ticker in ledger.get("positions", {}):
        return {"status": "already_open", "message": f"Position already open for {ticker}"}

    settings = _load_settings()
    max_positions = settings.get("max_positions", 12)
    base_pct = settings.get("position_size_pct", 0.08)
    conviction_scaling = settings.get("conviction_scaling", True)

    if len(ledger.get("positions", {})) >= max_positions:
        return {"status": "max_positions", "message": f"Max {max_positions} positions reached"}

    if shares is None:
        invest = _calc_position_size(ledger["cash"], confidence, base_pct, conviction_scaling)
        shares = round(invest / price, 4) if price > 0 else 0

    if shares <= 0:
        return {"status": "invalid", "message": f"Cannot buy 0 shares at ${price}"}

    cost = shares * price
    if cost > ledger["cash"]:
        shares = round(ledger["cash"] / price, 4) if price > 0 else 0
        cost = shares * price
        if cost > ledger["cash"]:
            return {"status": "insufficient_funds", "message": f"Need ${cost:.2f}, have ${ledger['cash']:.2f}"}

    ledger["cash"] -= cost
    ledger["positions"][ticker] = {
        "ticker": ticker,
        "shares": shares,
        "entry_price": round(price, 4),
        "last_price": round(price, 4),
        "confidence": confidence,
        "reasoning": reasoning,
        "task_id": task_id,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_ledger(ledger)
    return {"status": "ok", "message": f"Bought {shares} {ticker} @ ${price}", "cost": round(cost, 2)}


def sell(ticker: str, price: float, reasoning: str = "", task_id: str = ""):
    ledger = _load_ledger()
    ticker = ticker.upper()
    pos = ledger.get("positions", {}).pop(ticker, None)
    if not pos:
        return {"status": "no_position", "message": f"No open position for {ticker}"}

    proceeds = pos["shares"] * price
    pnl = proceeds - (pos["shares"] * pos["entry_price"])
    return_pct = (price - pos["entry_price"]) / pos["entry_price"] * 100 if pos["entry_price"] else 0
    hold_seconds = 0
    try:
        opened = datetime.fromisoformat(pos["opened_at"])
        hold_seconds = (datetime.now(timezone.utc) - opened).total_seconds()
    except Exception:
        pass

    ledger["cash"] += proceeds
    ledger["history"].append({
        "ticker": ticker,
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
    }


def _rotation_check(ledger: dict, ticker: str, confidence: float, price: float, reasoning: str, task_id: str) -> dict:
    """If max positions hit, find weakest holding and rotate if new opportunity is stronger."""
    settings = _load_settings()
    if not settings.get("enable_rotation", True):
        return {"status": "max_positions", "message": "Rotation disabled"}
    positions = ledger.get("positions", {})
    if len(positions) == 0:
        return {"status": "max_positions", "message": "No positions to rotate"}
    diff_threshold = settings.get("rotation_threshold_diff", 15)
    weakest = None
    weakest_score = float("inf")
    for t, pos in positions.items():
        ret = (pos.get("last_price", pos["entry_price"]) - pos["entry_price"]) / pos["entry_price"] * 100
        score = ret + pos.get("confidence", 0) * 0.1
        if score < weakest_score:
            weakest_score = score
            weakest = t
    if weakest and (confidence - positions[weakest].get("confidence", 0)) >= diff_threshold:
        wp = positions[weakest]
        sell_res = sell(weakest, wp.get("last_price", wp["entry_price"]), f"Rotated out for {ticker} ({confidence}% vs {wp['confidence']}%)", task_id)
        if sell_res.get("status") != "ok":
            return sell_res
        buy_res = buy(ticker, price, confidence, reasoning, task_id=task_id)
        buy_res["rotation"] = f"Sold {weakest} to buy {ticker}"
        return buy_res
    return {"status": "max_positions", "message": f"No rotation candidate"}


def auto_trade_from_result(result: dict) -> dict:
    """Auto-trade: buy on BUY/ACCUMULATE, sell on SELL/REDUCE for held positions."""
    # Refresh all position prices before making trade decisions
    ledger = _load_ledger()
    ledger = _update_prices(ledger)
    _save_ledger(ledger)
    
    settings = _load_settings()
    if not settings.get("auto_trade_enabled", True):
        return {"status": "skipped", "reason": "auto_trade_enabled=false"}

    rec = result.get("recommendation", "WATCH")
    conf = result.get("confidence", 0)
    ticker = result.get("ticker", "") or result.get("key_metrics", {}).get("ticker", "")
    price_raw = result.get("key_metrics", {}).get("current_price") or result.get("paper_trade_price", 0)
    price = float(price_raw) if price_raw is not None else 0.0
    if price <= 0:
        return {"status": "skipped", "reason": "missing price"}

    task_id = result.get("task_id", "")
    summary = result.get("summary", "")
    ledger = _load_ledger()  # Reload after price update

    # ── SELL logic: if we hold this ticker and it got SELL/REDUCE ──
    if rec in ("SELL", "REDUCE") and ticker.upper() in ledger.get("positions", {}):
        return sell(ticker, price, summary, task_id)

    # ── BUY logic ──
    if rec not in ("BUY", "ACCUMULATE"):
        return {"status": "skipped", "reason": f"rec={rec}"}

    threshold = settings.get("paper_trade_confidence_threshold", 60)
    max_pos = settings.get("max_positions", 12)

    if conf < threshold:
        return {"status": "skipped", "reason": f"conf={conf} < threshold={threshold}"}

    if len(ledger.get("positions", {})) >= max_pos:
        # Try rotation
        return _rotation_check(ledger, ticker, conf, price, summary, task_id)

    return buy(ticker, price, conf, summary, task_id=task_id)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    elif cmd == "buy" and len(sys.argv) >= 4:
        print(json.dumps(buy(sys.argv[2], float(sys.argv[3]), 80.0, "manual buy"), indent=2))
    elif cmd == "sell" and len(sys.argv) >= 3:
        try:
            import yfinance as yf_s
            t = yf_s.Ticker(sys.argv[2])
            hist = t.history(period="5d")  # Use 5d instead of 1d
            price = float(hist.Close.iloc[-1]) if len(hist) > 0 else float(sys.argv[3])
        except Exception:
            price = float(sys.argv[3]) if len(sys.argv) > 3 else 0
        print(json.dumps(sell(sys.argv[2], price), indent=2))
    else:
        print("Usage: python paper_trade.py [stats|buy TICKER PRICE|sell TICKER [PRICE]]")

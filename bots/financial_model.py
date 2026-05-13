"""
bots/financial_model.py
DCF + comparable analysis for intrinsic value estimation.
Usage: python bots/financial_model.py --ticker NVDA --output dashboard/data/models/NVDA.json
"""
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import random

def build_dcf(ticker: str) -> dict:
    """Simple 5-year DCF with mock assumptions."""
    current_fcf = random.uniform(2, 15)
    growth_rate = random.uniform(0.08, 0.25)
    terminal_growth = 0.03
    wacc = random.uniform(0.08, 0.12)
    shares = random.uniform(1e9, 3e9)
    
    # Project FCF
    fcfs = [current_fcf * (1 + growth_rate) ** i for i in range(1, 6)]
    # Terminal value
    terminal_value = fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
    # Discount
    pvs = [fcfs[i] / (1 + wacc) ** (i + 1) for i in range(5)]
    pv_terminal = terminal_value / (1 + wacc) ** 5
    enterprise_value = sum(pvs) + pv_terminal
    
    # Adjust for cash/debt mock
    net_cash = random.uniform(-5, 20)
    equity_value = enterprise_value + net_cash
    intrinsic_per_share = equity_value * 1e9 / shares if shares > 0 else 0
    
    return {
        "current_fcf_billions": round(current_fcf, 2),
        "projected_fcf_5yr": [round(f, 2) for f in fcfs],
        "growth_rate_assumed": round(growth_rate, 3),
        "wacc": round(wacc, 3),
        "terminal_growth": terminal_growth,
        "terminal_value_billions": round(terminal_value, 2),
        "enterprise_value_billions": round(enterprise_value, 2),
        "net_cash_billions": round(net_cash, 2),
        "equity_value_billions": round(equity_value, 2),
        "intrinsic_per_share": round(intrinsic_per_share, 2),
        "method": "DCF_5yr"
    }


def build_comparables(ticker: str) -> dict:
    """Mock peer multiples."""
    pe = round(random.uniform(12, 55), 2)
    ev_ebitda = round(random.uniform(8, 30), 2)
    ps = round(random.uniform(2, 15), 2)
    pb = round(random.uniform(2, 12), 2)
    
    current_price = round(random.uniform(50, 600), 2)
    eps = current_price / pe if pe > 0 else 0
    
    # Value based on peer median
    peer_median_pe = round(random.uniform(15, 35), 2)
    implied_price_pe = eps * peer_median_pe if eps > 0 else current_price
    
    return {
        "current_price": current_price,
        "trailing_pe": pe,
        "forward_pe": round(pe * random.uniform(0.6, 0.95), 2),
        "ev_ebitda": ev_ebitda,
        "price_to_sales": ps,
        "price_to_book": pb,
        "eps": round(eps, 2),
        "peer_median_pe": peer_median_pe,
        "implied_price_pe": round(implied_price_pe, 2),
        "upside_pct": round((implied_price_pe / current_price - 1) * 100, 2) if current_price > 0 else 0,
        "method": "peer_multiples"
    }


def build_model(ticker: str) -> dict:
    dcf = build_dcf(ticker)
    comps = build_comparables(ticker)
    
    # Blended target
    blended = round((dcf["intrinsic_per_share"] + comps["implied_price_pe"]) / 2, 2)
    margin_of_safety = round((blended - comps["current_price"]) / blended * 100, 2) if blended > 0 else 0
    
    return {
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_price": comps["current_price"],
        "dcf_target": dcf["intrinsic_per_share"],
        "comparable_target": comps["implied_price_pe"],
        "blended_target": blended,
        "margin_of_safety_pct": max(0, margin_of_safety),
        "dcf_model": dcf,
        "comparable_model": comps,
        "verdict": "Undervalued" if margin_of_safety > 20 else "Fairly valued" if margin_of_safety > 5 else "Overvalued"
    }


def run(args) -> bool:
    ticker = args.ticker.upper()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_model(ticker)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Model for {ticker}: {data['verdict']} | Blended target ${data['blended_target']} | MoS {data['margin_of_safety_pct']}%")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

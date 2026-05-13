"""
bots/earnings_analyzer.py
Extracts ticker, fetches earnings data, writes structured analysis.
Usage: python bots/earnings_analyzer.py --ticker NVDA --output dashboard/data/earnings/NVDA.json
"""
import argparse, json, os, re, sys, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def fetch_earnings_yahoo(ticker: str) -> dict:
    """Try yfinance for earnings dates and history."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}
        earnings_dates = t.earnings_dates
        dates_list = []
        if earnings_dates is not None:
            for idx, row in earnings_dates.head(4).iterrows():
                dates_list.append({
                    "date": str(idx)[:10],
                    "eps_estimate": row.get("EPS Estimate"),
                    "reported_eps": row.get("Reported EPS"),
                    "surprise_pct": row.get("Surprise(%)")
                })
        return {
            "next_earnings_date": info.get("earningsDate") if info and "earningsDate" in info else None,
            "earnings_history": dates_list,
            "pe_trailing": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "eps_ttm": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
        }
    except Exception as e:
        return {"_error": str(e)}


def generate_mock_earnings(ticker: str) -> dict:
    """Mock earnings data when real APIs unavailable."""
    base_eps = round(random.uniform(0.5, 8.0), 2)
    surprise = round(random.uniform(-15, 25), 1)
    return {
        "next_earnings_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(5, 45))).strftime("%Y-%m-%d"),
        "earnings_history": [
            {"date": "2026-02-28", "eps_estimate": round(base_eps - 0.2, 2), "reported_eps": base_eps, "surprise_pct": surprise},
            {"date": "2025-11-30", "eps_estimate": round(base_eps - 0.5, 2), "reported_eps": round(base_eps - 0.3, 2), "surprise_pct": round(surprise + random.uniform(-5, 5), 1)},
            {"date": "2025-08-30", "eps_estimate": round(base_eps - 0.8, 2), "reported_eps": round(base_eps - 0.6, 2), "surprise_pct": round(surprise + random.uniform(-3, 8), 1)},
        ],
        "eps_ttm": round(base_eps * 4, 2),
        "eps_forward": round(base_eps * 5.2, 2),
        "revenue_growth": round(random.uniform(-0.05, 0.35), 3),
        "earnings_growth": round(random.uniform(-0.1, 0.5), 3),
        "pe_trailing": round(random.uniform(15, 55), 2),
        "pe_forward": round(random.uniform(12, 45), 2),
        "peg_ratio": round(random.uniform(0.5, 2.5), 2),
    }


def analyze_earnings(ticker: str) -> dict:
    real = fetch_earnings_yahoo(ticker)
    if real and not real.get("_error") and real.get("earnings_history"):
        data = real
        source = "yahoo_finance"
    else:
        data = generate_mock_earnings(ticker)
        source = "mock_fallback"
    
    # Scoring
    surprise_avg = sum(e.get("surprise_pct", 0) for e in data.get("earnings_history", [])) / max(1, len(data.get("earnings_history", [])))
    revenue_growth = data.get("revenue_growth", 0) or 0
    earnings_growth = data.get("earnings_growth", 0) or 0
    
    catalyst_score = 0
    if surprise_avg > 5: catalyst_score += 30
    elif surprise_avg > 0: catalyst_score += 15
    if revenue_growth > 0.15: catalyst_score += 25
    elif revenue_growth > 0: catalyst_score += 10
    if earnings_growth > 0.2: catalyst_score += 25
    elif earnings_growth > 0: catalyst_score += 10
    
    data.update({
        "ticker": ticker.upper(),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "surprise_avg_pct": round(surprise_avg, 2),
        "earnings_catalyst_score": min(catalyst_score, 100),
        "verdict": "Strong earnings momentum" if catalyst_score > 60 else 
                   "Mixed earnings signals" if catalyst_score > 30 else "Earnings weakness detected",
    })
    return data


def run(args) -> bool:
    ticker = args.ticker.upper()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = analyze_earnings(ticker)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Earnings analysis for {ticker}: {data['verdict']} (catalyst score {data['earnings_catalyst_score']})")
    return True

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

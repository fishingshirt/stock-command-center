"""
bots/earnings_analyzer.py
Real earnings analysis using yfinance.
Produces: earnings trend, surprise history, catalyst score, verdict.
"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None


def analyze_earnings(ticker: str) -> dict:
    if yf is None:
        return {"_error": "yfinance not installed", "ticker": ticker.upper()}

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        # Earnings dates table
        earnings_dates = None
        try:
            earnings_dates = t.earnings_dates
        except Exception:
            pass

        dates_list = []
        next_earnings = None
        if earnings_dates is not None and hasattr(earnings_dates, 'iterrows'):
            for idx, row in earnings_dates.head(6).iterrows():
                date_str = str(idx)[:10]
                eps_est = row.get("EPS Estimate") if hasattr(row, 'get') else None
                reported = row.get("Reported EPS") if hasattr(row, 'get') else None
                surprise = row.get("Surprise(%)") if hasattr(row, 'get') else None
                rec = {
                    "date": date_str,
                    "eps_estimate": float(eps_est) if eps_est is not None else None,
                    "reported_eps": float(reported) if reported is not None else None,
                    "surprise_pct": float(surprise) if surprise is not None else None,
                }
                dates_list.append(rec)
                # Next earnings is first row with no reported EPS
                if next_earnings is None and rec["reported_eps"] is None:
                    next_earnings = date_str

        # Historical earnings (quarterly)
        quarterly_earnings = None
        try:
            quarterly_earnings = t.quarterly_earnings
        except Exception:
            pass

        q_history = []
        pe_trailing = info.get("trailingPE")
        pe_forward = info.get("forwardPE")
        peg = info.get("pegRatio")
        eps_ttm = info.get("trailingEps")
        eps_forward = info.get("forwardEps")
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")

        if quarterly_earnings is not None and hasattr(quarterly_earnings, 'iterrows'):
            for idx, row in quarterly_earnings.iterrows():
                try:
                    r_rev = row.get("Revenue")
                    r_earn = row.get("Earnings")
                    q_history.append({
                        "quarter": str(idx),
                        "revenue": float(r_rev) if r_rev is not None else None,
                        "earnings": float(r_earn) if r_earn is not None else None,
                    })
                except Exception:
                    pass

        # Calculate surprise average
        surprises = [d["surprise_pct"] for d in dates_list if d["surprise_pct"] is not None]
        surprise_avg = round(sum(surprises) / len(surprises), 2) if surprises else None

        # Calculate EPS trajectory
        eps_dates = [d for d in dates_list if d["reported_eps"] is not None]
        eps_trend = "FLAT"
        if len(eps_dates) >= 2:
            first = eps_dates[-1]["reported_eps"]
            last = eps_dates[0]["reported_eps"]
            if last > first * 1.1:
                eps_trend = "ACCELERATING"
            elif last < first * 0.9:
                eps_trend = "DECLINING"
            else:
                eps_trend = "STABLE"

        # Scoring
        catalyst_score = 0
        if surprise_avg is not None:
            if surprise_avg > 10:
                catalyst_score += 35
            elif surprise_avg > 5:
                catalyst_score += 20
            elif surprise_avg > 0:
                catalyst_score += 10
        if revenue_growth is not None:
            if revenue_growth > 0.20:
                catalyst_score += 25
            elif revenue_growth > 0.10:
                catalyst_score += 15
            elif revenue_growth > 0:
                catalyst_score += 5
        if earnings_growth is not None:
            if earnings_growth > 0.25:
                catalyst_score += 25
            elif earnings_growth > 0.15:
                catalyst_score += 15
            elif earnings_growth > 0:
                catalyst_score += 5
        if eps_trend == "ACCELERATING":
            catalyst_score += 10
        elif eps_trend == "DECLINING":
            catalyst_score -= 10

        catalyst_score = max(0, min(100, catalyst_score))

        if catalyst_score > 65:
            verdict = "Strong earnings momentum"
        elif catalyst_score > 40:
            verdict = "Solid earnings trend"
        elif catalyst_score > 20:
            verdict = "Mixed earnings signals"
        else:
            verdict = "Earnings weakness detected"

        # Next earnings proximity — if within 2 weeks, flag
        days_to_earnings = None
        if next_earnings:
            try:
                next_dt = datetime.strptime(next_earnings, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_to_earnings = (next_dt - datetime.now(timezone.utc)).days
            except Exception:
                pass

        return {
            "ticker": ticker.upper(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "next_earnings_date": next_earnings,
            "days_to_earnings": days_to_earnings,
            "earnings_dates": dates_list,
            "quarterly_history": q_history[:8],
            "pe_trailing": pe_trailing,
            "pe_forward": pe_forward,
            "peg_ratio": peg,
            "eps_ttm": eps_ttm,
            "eps_forward": eps_forward,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "surprise_avg_pct": surprise_avg,
            "eps_trend": eps_trend,
            "earnings_catalyst_score": catalyst_score,
            "verdict": verdict,
        }

    except Exception as e:
        return {"_error": str(e), "ticker": ticker.upper()}


def run(args) -> bool:
    ticker = args.ticker.upper()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = analyze_earnings(ticker)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if data.get("_error"):
        print(f"Earnings {ticker}: ERROR — {data['_error']}")
    else:
        print(f"Earnings {ticker}: {data['verdict']} (catalyst {data['earnings_catalyst_score']}) | EPS trend: {data['eps_trend']} | Next: {data.get('next_earnings_date', 'N/A')}")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

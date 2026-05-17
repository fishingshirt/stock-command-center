"""
bots/financial_model.py
Real valuation model using actual yfinance data.
Produces: DCF target, comparable valuation, margin of safety, verdict.
"""
import argparse, json, sys, math
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None


def build_model(ticker: str) -> dict:
    if yf is None:
        return {"_error": "yfinance not installed", "ticker": ticker.upper()}

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="1y")

        current_price = round(float(hist["Close"].iloc[-1]), 2) if len(hist) > 0 else info.get("currentPrice") or info.get("previousClose") or 0
        if not current_price:
            return {"_error": "No price data available", "ticker": ticker.upper()}

        # ── Comparable Analysis ──
        pe = info.get("trailingPE")
        pe_forward = info.get("forwardPE")
        ps = info.get("priceToSalesTrailing12Months")
        pb = info.get("priceToBook")
        ev_ebitda = info.get("enterpriseToEbitda")
        eps = info.get("trailingEps")
        eps_forward = info.get("forwardEps")
        revenue_per_share = info.get("revenuePerShare")
        book_value = info.get("bookValue")

        # Get sector medians from info if available, else use rough sector proxies
        sector = info.get("sector", "")
        sector_pe_medians = {
            "Technology": 28, "Healthcare": 22, "Energy": 12,
            "Financial Services": 15, "Communication Services": 20,
            "Consumer Cyclical": 22, "Consumer Defensive": 20,
            "Industrials": 18, "Utilities": 16, "Real Estate": 18,
        }
        sector_ps_medians = {
            "Technology": 8, "Healthcare": 4, "Energy": 1.5,
            "Financial Services": 3, "Communication Services": 3,
            "Consumer Cyclical": 1.5, "Consumer Defensive": 2,
            "Industrials": 2, "Utilities": 2.5, "Real Estate": 4,
        }
        median_pe = sector_pe_medians.get(sector, 22)
        median_ps = sector_ps_medians.get(sector, 3)

        implied_pe = None
        implied_ps = None
        implied_pb = None
        if eps and eps > 0 and median_pe:
            implied_pe = round(eps * median_pe, 2)
        if revenue_per_share and revenue_per_share > 0 and median_ps:
            implied_ps = round(revenue_per_share * median_ps, 2)
        if book_value and book_value > 0 and pb:
            sector_pb_med = 3.0 if sector == "Technology" else 2.0
            implied_pb = round(book_value * sector_pb_med, 2)

        comparable_values = [v for v in [implied_pe, implied_ps, implied_pb] if v]
        comparable_target = round(sum(comparable_values) / len(comparable_values), 2) if comparable_values else current_price

        # ── Simple DCF ──
        # Use freeCashflow from yfinance if available
        fcf = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")
        growth_5yr = info.get("earningsGrowth", 0.15)
        if growth_5yr is None or growth_5yr < 0.02:
            growth_5yr = 0.10  # conservative default
        wacc = 0.09
        terminal_growth = 0.025

        dcf_intrinsic = None
        if fcf and fcf > 0 and shares and shares > 0:
            fcfs = [fcf * (1 + growth_5yr) ** i for i in range(1, 6)]
            terminal_value = fcfs[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
            pvs = [fcfs[i] / (1 + wacc) ** (i + 1) for i in range(5)]
            pv_terminal = terminal_value / (1 + wacc) ** 5
            enterprise_value = sum(pvs) + pv_terminal
            net_cash = (info.get("totalCash") or 0) - (info.get("totalDebt") or 0)
            equity_value = enterprise_value + net_cash
            dcf_intrinsic = round(equity_value / shares, 2)

        # ── Blended Target ──
        targets = [v for v in [dcf_intrinsic, comparable_target] if v]
        blended = round(sum(targets) / len(targets), 2) if targets else current_price

        margin_of_safety = round((blended - current_price) / blended * 100, 2) if blended > 0 else 0

        # ── Verdict ──
        if margin_of_safety > 20:
            verdict = "STRONG_BUY" if margin_of_safety > 30 else "BUY"
        elif margin_of_safety > 5:
            verdict = "FAIRLY_VALUED"
        elif margin_of_safety > -10:
            verdict = "SLIGHTLY_OVERVALUED"
        else:
            verdict = "OVERVALUED"

        return {
            "ticker": ticker.upper(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_price": current_price,
            "dcf_target": dcf_intrinsic,
            "comparable_target": comparable_target,
            "blended_target": blended,
            "margin_of_safety_pct": max(0, margin_of_safety),
            "upside_pct": round((blended - current_price) / current_price * 100, 2) if current_price else 0,
            "verdict": verdict,
            "valuation_inputs": {
                "trailing_pe": pe,
                "forward_pe": pe_forward,
                "price_to_sales": ps,
                "price_to_book": pb,
                "ev_ebitda": ev_ebitda,
                "eps_ttm": eps,
                "eps_forward": eps_forward,
                "sector": sector,
                "sector_median_pe": median_pe,
                "implied_pe": implied_pe,
                "implied_ps": implied_ps,
                "implied_pb": implied_pb,
                "free_cash_flow": fcf,
                "shares_outstanding": shares,
                "growth_assumed": round(growth_5yr, 3),
                "wacc": wacc,
                "terminal_growth": terminal_growth,
            },
        }

    except Exception as e:
        return {"_error": str(e), "ticker": ticker.upper()}


def run(args) -> bool:
    ticker = args.ticker.upper()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_model(ticker)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if data.get("_error"):
        print(f"Model {ticker}: ERROR — {data['_error']}")
    else:
        print(f"Model {ticker}: {data['verdict']} | Target ${data['blended_target']} | MoS {data['margin_of_safety_pct']}% | Upside {data.get('upside_pct', 0)}%")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

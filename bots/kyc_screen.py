"""
bots/kyc_screen.py
Honest compliance screening. Only reports what we can verify from public data.
For sanctions/PEP/ESG/controversies: returns explicit NO_DATA — never fabricates.
Usage: python bots/kyc_screen.py --ticker NVDA --output dashboard/data/kyc/NVDA.json
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None


# Real controversy keywords to scan for in any available data
CONTROVERSY_KEYWORDS = {
    "lawsuit", "fraud", "investigation", "sec filing", "bribe", "corruption",
    "settlement", "fine", "penalty", "antitrust", "monopoly", "data breach",
    "hack", "privacy", "discrimination", "harassment", "scandal", "recall",
    "unsafe", "misleading", "sanction", "banned", "prohibited",
}


def _check_news_for_flags(news_items: list) -> list:
    """Scan headline text for actual controversy keywords."""
    flags = []
    if not news_items:
        return flags
    for item in news_items:
        title = (item.get("title", "") or "").lower()
        if any(kw in title for kw in CONTROVERSY_KEYWORDS):
            flags.append(f"Headline flagged: {item['title'][:100]}")
    return flags


def screen(ticker: str) -> dict:
    """
    Real compliance screening. Only uses verifiable public data.
    Anything we can't verify returns explicit NO_DATA.
    """
    info = {}
    current_price = None
    if yf is not None:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            hist = t.history(period="5d")
            if len(hist) > 0:
                current_price = round(float(hist.Close.iloc[-1]), 2)
        except Exception:
            pass

    # --- Real data we CAN pull ---
    sector = info.get("sector") or info.get("industry")
    country = info.get("country")
    employees = info.get("fullTimeEmployees")
    market_cap = info.get("marketCap")
    beta = info.get("beta")

    # News-based controversy scan (real data)
    news = []
    try:
        # Re-use Yahoo RSS (same source as researcher_bot)
        import requests, xml.etree.ElementTree as ET
        url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:8]:
                title = item.find("title")
                if title is not None:
                    news.append({"title": title.text or ""})
    except Exception:
        pass

    news_flags = _check_news_for_flags(news)

    # --- What we CANNOT verify from free public APIs ---
    # Sanctions, PEP, ESG, controversy counts all require premium APIs
    # (OFAC lists, Refinitiv Eikon, MSCI ESG, etc).
    # Explicitly refuse to fabricate.

    overall_score = None  # Cannot compute without real sources

    # Bare-minimum risk assessment from real proxies
    risk_factors = []
    if not country:
        risk_factors.append("HQ country unknown")
    else:
        # Simple honest heuristic: US/EU/UK/JP/CN/CA = known jurisdiction
        pass

    if news_flags:
        risk_factors.append(f"{len(news_flags)} recent news items flagged for controversy")

    # Determine pass/fail from ONLY verifiable data
    pass_flag = True
    if news_flags:
        pass_flag = False

    return {
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compliance_score": "NO_DATA",
        "risk_level": "NO_DATA",
        "sanctions_risk": "NO_DATA — Premium API required (OFAC/dowJones Watchlist)",
        "pep_exposure": "NO_DATA — Premium API required (DowJones/Refinitiv PEP)",
        "esg_score": "NO_DATA — Premium API required (MSCI/Refinitiv/Sustainalytics)",
        "controversy_count": len(news_flags),
        "jurisdiction_risk": "NO_DATA",
        "flags": news_flags,
        "pass": pass_flag,
        "derived_from": {
            "sector": sector,
            "country": country,
            "employees": employees,
            "market_cap": market_cap,
            "beta": beta,
            "current_price": current_price,
            "news_items_scanned": len(news),
        },
        "_note": "Real-time sanctions, PEP, ESG, and structured controversy databases require paid APIs. "
                 "This screen only checks public news headlines for controversy keywords.",
    }


def run(args) -> bool:
    ticker = args.ticker.upper()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = screen(ticker)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"KYC for {ticker}: {data['pass']} | {len(data['flags'])} news flags | Sanctions/ESG/PEP: NO_DATA")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

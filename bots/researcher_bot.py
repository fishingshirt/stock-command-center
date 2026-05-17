"""
bots/researcher_bot.py
Stock Command Center — Real Market Intelligence Engine
Fetches actual market data via yfinance, computes technical indicators,
analyzes news sentiment, and produces actionable BUY/SELL/HOLD recommendations.
"""
import argparse
import json
import os
import re
import sys
import math
from datetime import datetime, timezone
from pathlib import Path

parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

import requests
import xml.etree.ElementTree as ET

try:
    import yfinance as yf
except ImportError:
    yf = None

# ── Config ─────────────────────────────────────────────────────────

BULLISH_WORDS = {
    "surge", "rally", "gain", "beat", "strong", "bull", "buy", "upgrade", "outperform",
    "growth", "breakout", "moon", "rocket", "ath", "all-time high", "bullish", "beats",
    "raises guidance", "dividend hike", "partnership", "contract win", "fda approval",
    "earnings beat", "revenue beat", "guidance raise", "momentum", "rallying", "soar",
    "explodes", "jumps", "climbs", "surges", "rallies", "gains"
}

BEARISH_WORDS = {
    "drop", "fall", "crash", "bear", "sell", "downgrade", "underperform", "loss",
    "miss", "weak", "recession", "layoff", "lawsuit", "sec", "investigation", "bearish",
    "cuts guidance", "dividend cut", "recall", "data breach", "fraud", "investigation",
    "tumbles", "plunges", "dives", "crashes", "slumps", "falls", "drops", "misses",
    "slashes", "warns", "delays", "restructure"
}

WATCHLIST = [
    "SPY", "QQQ", "IWM", "VTI", "VOO", "VGT", "XLK", "XLF", "XLE", "XLI",
    "NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "AMD", "AVGO", "CRM",
    "JPM", "BAC", "GS", "XOM", "CVX", "UNH", "JNJ", "LLY", "PFE",
    "DIS", "NFLX", "PYPL", "UBER", "COIN", "PLTR", "ARKK",
    "BTC-USD", "ETH-USD", "SOL-USD",
]


# ── Data Fetch ─────────────────────────────────────────────────────

def fetch_stock_data(ticker: str) -> dict:
    """Fetch comprehensive stock data from yfinance."""
    if yf is None:
        return {"_error": "yfinance not installed"}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist_3mo = t.history(period="3mo")
        hist_1y = t.history(period="1y")

        if len(hist_3mo) < 20:
            return {"_error": f"Insufficient price history for {ticker}"}

        prices = hist_3mo["Close"].tolist()
        current_price = round(prices[-1], 2)
        prev_close = round(prices[-2], 2) if len(prices) > 1 else current_price
        day_change_pct = round((current_price - prev_close) / prev_close * 100, 2)

        sma_20 = _calc_sma(prices, 20)
        sma_50 = _calc_sma(prices, 50) if len(prices) >= 50 else None
        sma_200 = _calc_sma(hist_1y["Close"].tolist(), 200) if len(hist_1y) >= 200 else None
        rsi_14 = _calc_rsi(prices, 14)

        high_52w = info.get("fiftyTwoWeekHigh")
        low_52w = info.get("fiftyTwoWeekLow")
        price_vs_52w = None
        if high_52w and low_52w and high_52w != low_52w:
            price_vs_52w = round((current_price - low_52w) / (high_52w - low_52w) * 100, 1)

        avg_vol = info.get("averageVolume", 0)
        recent_vol = hist_3mo["Volume"].iloc[-5:].mean() if len(hist_3mo) >= 5 else 0
        volume_surge = None
        if avg_vol and avg_vol > 0:
            volume_surge = round(recent_vol / avg_vol, 2)

        market_cap = info.get("marketCap")
        pe_trailing = info.get("trailingPE")
        pe_forward = info.get("forwardPE")
        peg = info.get("pegRatio")
        eps_ttm = info.get("trailingEps")
        eps_forward = info.get("forwardEps")
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")
        profit_margin = info.get("profitMargins")
        short_ratio = info.get("shortRatio")
        beta = info.get("beta")

        # Momentum: 5d, 1mo, 3mo returns
        ret_5d = _calc_return(prices, 5)
        ret_1mo = _calc_return(prices, 20)
        ret_3mo = _calc_return(prices, min(63, len(prices)))

        return {
            "ticker": ticker,
            "current_price": current_price,
            "previous_close": prev_close,
            "day_change_pct": day_change_pct,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi_14": rsi_14,
            "52_week_high": high_52w,
            "52_week_low": low_52w,
            "price_vs_52w_pct": price_vs_52w,
            "volume_surge": volume_surge,
            "avg_volume": avg_vol,
            "market_cap": market_cap,
            "pe_trailing": pe_trailing,
            "pe_forward": pe_forward,
            "peg_ratio": peg,
            "eps_ttm": eps_ttm,
            "eps_forward": eps_forward,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "profit_margin": profit_margin,
            "short_ratio": short_ratio,
            "beta": beta,
            "return_5d_pct": ret_5d,
            "return_1mo_pct": ret_1mo,
            "return_3mo_pct": ret_3mo,
            "_source": "yfinance",
        }
    except Exception as e:
        return {"_error": str(e)}


def fetch_crypto_data(ticker: str) -> dict:
    """Fetch crypto data from CoinGecko or yfinance fallback."""
    # Map tickers
    coin_map = {
        "BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    }
    coin_id = coin_map.get(ticker, ticker.lower().replace("-usd", ""))
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={coin_id}"
        r = requests.get(url, timeout=20)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            d = data[0]
            price = d.get("current_price")
            return {
                "ticker": ticker,
                "current_price": price,
                "market_cap": d.get("market_cap"),
                "total_volume": d.get("total_volume"),
                "day_change_pct": d.get("price_change_percentage_24h"),
                "ath": d.get("ath"),
                "ath_change_pct": d.get("ath_change_percentage"),
                "_source": "coingecko",
            }
    except Exception:
        pass
    # yfinance fallback
    if yf is not None:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            info = t.info or {}
            current_price = float(hist.Close.iloc[-1]) if len(hist) > 0 else None
            return {
                "ticker": ticker,
                "current_price": round(current_price, 2) if current_price else None,
                "market_cap": info.get("marketCap"),
                "_source": "yfinance",
            }
        except Exception:
            pass
    return {"_error": f"Could not fetch crypto data for {ticker}"}


# ── Technicals ─────────────────────────────────────────────────────

def _calc_sma(prices: list, period: int) -> float | None:
    if len(prices) >= period:
        return round(sum(prices[-period:]) / period, 2)
    return None


def _calc_rsi(prices: list, period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _calc_return(prices: list, days: int) -> float | None:
    if len(prices) >= days:
        return round((prices[-1] - prices[-days]) / prices[-days] * 100, 2)
    return None


# ── News ───────────────────────────────────────────────────────────

def fetch_yahoo_news(ticker: str) -> list:
    """Fetch latest news from Yahoo Finance RSS."""
    try:
        url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        news = []
        for item in items[:8]:
            title = item.find("title")
            pub = item.find("pubDate")
            link = item.find("link")
            if title is not None:
                news.append({
                    "title": title.text or "",
                    "published": pub.text if pub is not None else "",
                    "url": link.text if link is not None else "",
                    "source": "Yahoo Finance",
                })
        return news
    except Exception:
        return []


def analyze_sentiment(news_items: list) -> dict:
    """Keyword-based sentiment from news headlines."""
    if not news_items:
        return {"score": 0, "label": "NEUTRAL", "bullish": 0, "bearish": 0}
    bullish = 0
    bearish = 0
    for item in news_items:
        title = item.get("title", "").lower()
        words = set(re.findall(r'\b\w+\b', title))
        bullish += len(words & BULLISH_WORDS)
        bearish += len(words & BEARISH_WORDS)
    total = bullish + bearish
    if total == 0:
        return {"score": 0, "label": "NEUTRAL", "bullish": 0, "bearish": 0}
    score = round((bullish - bearish) / total * 100, 1)
    label = "BULLISH" if score > 20 else "BEARISH" if score < -20 else "NEUTRAL"
    return {"score": score, "label": label, "bullish": bullish, "bearish": bearish, "total_mentions": total}


# ── Signal Scoring ─────────────────────────────────────────────────

def compute_signals(metrics: dict, sentiment: dict, news: list) -> dict:
    """
    Compute weighted buy/sell signals from real data.
    Returns dict with signal scores and recommendation.
    """
    signals = []
    reasons = []
    warnings = []

    price = metrics.get("current_price")
    pe_t = metrics.get("pe_trailing")
    pe_f = metrics.get("pe_forward")
    rsi = metrics.get("rsi_14")
    sma20 = metrics.get("sma_20")
    sma50 = metrics.get("sma_50")
    sma200 = metrics.get("sma_200")
    ret_5d = metrics.get("return_5d_pct")
    ret_1mo = metrics.get("return_1mo_pct")
    ret_3mo = metrics.get("return_3mo_pct")
    vol_surge = metrics.get("volume_surge")
    price_vs_52w = metrics.get("price_vs_52w_pct")
    day_change = metrics.get("day_change_pct")
    sentiment_label = sentiment.get("label", "NEUTRAL")
    sentiment_score = sentiment.get("score", 0)
    peg = metrics.get("peg_ratio")
    rev_growth = metrics.get("revenue_growth")
    earn_growth = metrics.get("earnings_growth")

    # 1. Momentum signals
    if ret_1mo is not None and ret_1mo > 10:
        signals.append(("1mo_momentum", 1.5, f"Strong 1mo momentum +{ret_1mo}%"))
    elif ret_1mo is not None and ret_1mo > 5:
        signals.append(("1mo_momentum", 1.0, f"Positive 1mo momentum +{ret_1mo}%"))
    elif ret_1mo is not None and ret_1mo < -10:
        signals.append(("1mo_momentum", -1.5, f"Weak 1mo momentum {ret_1mo}%"))
    elif ret_1mo is not None and ret_1mo < -5:
        signals.append(("1mo_momentum", -0.5, f"Negative 1mo momentum {ret_1mo}%"))

    if ret_3mo is not None and ret_3mo > 15:
        signals.append(("3mo_momentum", 1.5, f"Strong 3mo momentum +{ret_3mo}%"))
    elif ret_3mo is not None and ret_3mo < -15:
        signals.append(("3mo_momentum", -1.5, f"Weak 3mo momentum {ret_3mo}%"))

    if day_change is not None and day_change > 3:
        signals.append(("day_spike", 0.5, f"Big daily move +{day_change}%"))
    elif day_change is not None and day_change < -3:
        signals.append(("day_spike", -0.5, f"Big daily drop {day_change}%"))

    # 2. RSI signals
    if rsi is not None:
        if rsi > 75:
            signals.append(("rsi", -2.0, f"RSI extremely overbought {rsi}"))
            warnings.append(f"RSI {rsi} — possible reversal risk")
        elif rsi > 65:
            signals.append(("rsi", -1.0, f"RSI overbought {rsi}"))
        elif rsi < 25:
            signals.append(("rsi", 2.0, f"RSI extremely oversold {rsi}"))
            reasons.append(f"RSI {rsi} — oversold bounce potential")
        elif rsi < 35:
            signals.append(("rsi", 1.0, f"RSI oversold {rsi}"))
            reasons.append(f"RSI {rsi} — approaching oversold")

    # 3. SMA signals
    if price and sma20:
        if price > sma20 * 1.02:
            signals.append(("sma20", 0.5, f"Price above SMA20 ({sma20})"))
        elif price < sma20 * 0.98:
            signals.append(("sma20", -0.5, f"Price below SMA20 ({sma20})"))
    if sma20 and sma50:
        if sma20 > sma50 * 1.01:
            signals.append(("golden_cross", 1.0, "SMA20 > SMA50 (short-term uptrend)"))
        elif sma20 < sma50 * 0.99:
            signals.append(("death_cross", -1.0, "SMA20 < SMA50 (short-term downtrend)"))
    if price and sma200:
        if price > sma200 * 1.05:
            signals.append(("sma200", 1.0, f"Price well above SMA200 ({sma200}) — confirmed uptrend"))
        elif price < sma200 * 0.95:
            signals.append(("sma200", -1.0, f"Price below SMA200 ({sma200}) — confirmed downtrend"))

    # 4. Valuation signals
    if pe_t is not None:
        if pe_t < 15:
            signals.append(("pe", 1.5, f"Low trailing P/E {pe_t}x — value opportunity"))
            reasons.append(f"Trailing P/E {pe_t}x — below market average")
        elif pe_t > 40:
            signals.append(("pe", -1.5, f"High trailing P/E {pe_t}x — stretched valuation"))
            warnings.append(f"High P/E {pe_t}x — growth expectations priced in")
        elif pe_t > 30:
            signals.append(("pe", -0.5, f"Elevated P/E {pe_t}x"))

    if pe_f is not None and pe_t is not None:
        if pe_f < pe_t * 0.8:
            signals.append(("pe_forward", 1.0, f"Forward P/E {pe_f}x < trailing {pe_t}x (expected growth)"))
        elif pe_f > pe_t * 1.2:
            signals.append(("pe_forward", -0.5, f"Forward P/E {pe_f}x > trailing {pe_t}x (expected slowdown)"))

    if peg is not None:
        if peg < 1.0:
            signals.append(("peg", 1.0, f"PEG {peg} < 1.0 — growth cheap vs price"))
        elif peg > 2.0:
            signals.append(("peg", -1.0, f"PEG {peg} > 2.0 — expensive growth"))

    # 5. Growth signals
    if rev_growth is not None:
        if rev_growth > 0.20:
            signals.append(("revenue_growth", 1.5, f"Revenue growing {rev_growth*100:.0f}% YoY"))
        elif rev_growth > 0.10:
            signals.append(("revenue_growth", 1.0, f"Revenue growing {rev_growth*100:.0f}% YoY"))
        elif rev_growth < -0.05:
            signals.append(("revenue_growth", -1.0, f"Revenue declining {rev_growth*100:.0f}% YoY"))

    if earn_growth is not None:
        if earn_growth > 0.20:
            signals.append(("earnings_growth", 1.0, f"Earnings growing {earn_growth*100:.0f}% YoY"))
        elif earn_growth < -0.10:
            signals.append(("earnings_growth", -1.0, f"Earnings declining {earn_growth*100:.0f}% YoY"))

    # 6. 52-week position
    if price_vs_52w is not None:
        if price_vs_52w > 90:
            signals.append(("52w", -1.0, f"Near 52-week high ({price_vs_52w}% of range)"))
            warnings.append(f"Price at {price_vs_52w}% of 52-week range — limited upside")
        elif price_vs_52w < 10:
            signals.append(("52w", 1.0, f"Near 52-week low ({price_vs_52w}% of range)"))
            reasons.append(f"Price near 52-week low — potential value entry")

    # 7. Volume surge
    if vol_surge is not None and vol_surge > 2.0:
        signals.append(("volume", 0.5, f"Volume surge {vol_surge}x average"))

    # 8. Sentiment
    if sentiment_label == "BULLISH":
        signals.append(("sentiment", 1.0 if sentiment_score > 30 else 0.5, f"Bullish news sentiment ({sentiment_score})"))
        reasons.append(f"Bullish news sentiment detected")
    elif sentiment_label == "BEARISH":
        signals.append(("sentiment", -1.0 if sentiment_score < -30 else -0.5, f"Bearish news sentiment ({sentiment_score})"))
        warnings.append(f"Bearish news sentiment detected")

    # ── Sum signals ──
    total_score = sum(s[1] for s in signals)
    max_possible = sum(abs(s[1]) for s in signals) if signals else 1
    normalized = total_score / max_possible if max_possible > 0 else 0

    # Determine recommendation
    if normalized > 0.4:
        rec = "BUY"
        conf = min(95, int(70 + normalized * 25))
    elif normalized > 0.15:
        rec = "ACCUMULATE"
        conf = min(85, int(60 + normalized * 25))
    elif normalized < -0.4:
        rec = "SELL"
        conf = min(90, int(65 + abs(normalized) * 25))
    elif normalized < -0.15:
        rec = "HOLD"
        conf = min(70, int(50 + abs(normalized) * 20))
        # But flag as weak hold, could be reduce
        if warnings:
            rec = "REDUCE"
            conf = min(75, int(55 + abs(normalized) * 20))
    else:
        rec = "HOLD"
        conf = int(50 + abs(normalized) * 20)

    # Strategy classification
    strategy = "GROWTH"
    if pe_t and pe_t < 20 and normalized > 0:
        strategy = "VALUE"
    elif ret_1mo and ret_1mo > 10 and normalized > 0:
        strategy = "MOMENTUM"
    elif pe_t and pe_t > 30 and earn_growth and earn_growth > 0.15:
        strategy = "GROWTH"
    elif pe_t and pe_t < 25 and earn_growth and earn_growth > 0.10 and normalized > 0:
        strategy = "QUALITY"
    elif price and metrics.get("dividendYield"):
        strategy = "INCOME"

    return {
        "recommendation": rec,
        "confidence": conf,
        "signal_score": round(normalized, 3),
        "signals": [{"name": s[0], "score": s[1], "note": s[2]} for s in signals],
        "reasons": reasons,
        "warnings": warnings,
        "strategy": strategy,
        "sentiment": sentiment,
    }


# ── Main Runner ────────────────────────────────────────────────────

def analyze_ticker(ticker: str, task_id: str = "", subject: str = "") -> dict:
    """Full analysis pipeline for a single ticker."""
    is_crypto = ticker in ("BTC-USD", "ETH-USD", "SOL-USD", "BTC", "ETH", "SOL")

    if is_crypto:
        metrics = fetch_crypto_data(ticker)
        asset_type = "crypto"
    else:
        metrics = fetch_stock_data(ticker)
        asset_type = "stock"

    if metrics.get("_error"):
        return {
            "task_id": task_id,
            "subject": subject,
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendation": "NO_DATA",
            "confidence": 0,
            "summary": f"Data unavailable for {ticker}: {metrics['_error']}",
            "key_metrics": metrics,
            "asset_type": asset_type,
        }

    news = fetch_yahoo_news(ticker)
    sentiment = analyze_sentiment(news)
    signals = compute_signals(metrics, sentiment, news)

    price = metrics.get("current_price", 0) or 0

    # Build summary
    summary_parts = [
        f"{ticker} @ ${price} — {signals['recommendation']} ({signals['confidence']}% confidence)",
    ]
    if signals["reasons"]:
        summary_parts.append("Bullish: " + "; ".join(signals["reasons"][:2]))
    if signals["warnings"]:
        summary_parts.append("Warnings: " + "; ".join(signals["warnings"][:2]))
    if metrics.get("rsi_14") is not None:
        summary_parts.append(f"RSI: {metrics['rsi_14']}")
    if metrics.get("pe_trailing") is not None:
        summary_parts.append(f"P/E: {metrics['pe_trailing']}")
    summary_parts.append(f"Strategy: {signals['strategy']}")

    return {
        "task_id": task_id,
        "subject": subject or f"{ticker} analysis",
        "ticker": ticker,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommendation": signals["recommendation"],
        "confidence": signals["confidence"],
        "summary": " | ".join(summary_parts),
        "signal_score": signals["signal_score"],
        "strategy": signals["strategy"],
        "key_metrics": metrics,
        "signals": signals["signals"],
        "reasons": signals["reasons"],
        "warnings": signals["warnings"],
        "sentiment": sentiment,
        "news": news[:5] if news else [],
        "sources": [f"https://finance.yahoo.com/quote/{ticker}" if asset_type == "stock" else f"https://www.coingecko.com/en/coins/{ticker.lower()}"],
        "paper_trade_signal": signals["recommendation"],
        "paper_trade_price": price,
        "asset_type": asset_type,
    }


def run(args) -> bool:
    ticker = args.ticker if hasattr(args, 'ticker') and args.ticker else None
    if not ticker:
        # Try extract from subject
        m = re.search(r'\b([A-Z]{2,5}(?:-USD)?)\b', getattr(args, 'subject', '') or '')
        ticker = m.group(1) if m else "SPY"

    result = analyze_ticker(
        ticker=ticker,
        task_id=getattr(args, 'task_id', ''),
        subject=getattr(args, 'subject', '')
    )

    output_path = Path(getattr(args, 'output', f'dashboard/data/output/{datetime.now(timezone.utc).strftime("%Y%m%d")}-{ticker}.json'))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"{ticker}: {result['recommendation']} ({result['confidence']}%) — {result['summary'][:160]}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock/Crypto Research Bot v2")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--subject", default="")
    parser.add_argument("--details", default="")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    success = run(args)
    sys.exit(0 if success else 1)

"""
bots/researcher_bot.py
Domain expert worker. Gathers stock/crypto data and writes structured result JSON.
Usage:
  python bots/researcher_bot.py --task-id ID --subject "NVDA earnings risk" --details "..." --output path.json
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import requests
except ImportError:
    requests = None


def infer_ticker(subject: str) -> tuple:
    """Try to extract a stock or crypto ticker from the subject text."""
    known_stocks = {
        "nvda": "NVDA", "tsla": "TSLA", "aapl": "AAPL", "amzn": "AMZN",
        "msft": "MSFT", "goog": "GOOGL", "meta": "META", "nflx": "NFLX",
        "amd": "AMD", "intc": "INTC", "crm": "CRM", "adbe": "ADBE",
        "pypl": "PYPL", "uber": "UBER", "lyft": "LYFT", "coin": "COIN",
        "dis": "DIS", "ba": "BA", "ko": "KO", "pep": "PEP", "jnj": "JNJ",
        "pfe": "PFE", "unh": "UNH", "xom": "XOM", "cvx": "CVX",
        "jpm": "JPM", "gs": "GS", "bac": "BAC", "c": "C",
    }
    subj_lower = subject.lower()
    known_crypto = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "bnb": "binancecoin", "ada": "cardano", "xrp": "ripple",
        "dot": "polkadot", "avax": "avalanche-2", "matic": "matic-network",
        "doge": "dogecoin", "shib": "shiba-inu", "ltc": "litecoin",
    }
    for sym, full in known_crypto.items():
        if re.search(rf'\b{re.escape(sym)}\b', subj_lower) or full.replace("-", " ") in subj_lower:
            return (sym.upper(), "crypto", full)
    for sym, ticker in known_stocks.items():
        if re.search(rf'\b{re.escape(sym)}\b', subj_lower) or re.search(rf'\b{re.escape(ticker.lower())}\b', subj_lower):
            return (ticker, "stock", None)
    generic_blocklist = {
        "A", "AN", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AT", "BY", "WITH", "FROM",
        "S", "P", "C", "T", "B", "X", "V", "I", "R", "E", "N", "D", "G", "F", "Y", "Q",
        "SP", "TOP", "AUTO", "SCAN",
    }
    m = re.search(r'\b([A-Z]{2,5})\b', subject)
    if m:
        cand = m.group(1)
        if cand not in generic_blocklist:
            return (cand, "stock", None)
    return ("SPY", "stock", None)


def fetch_stock_yfinance(ticker: str) -> dict | None:
    if yf is None:
        return None
    # Try yfinance first
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        info = t.info or {}
        current_price = float(hist.Close.iloc[-1]) if len(hist) > 0 else None
        prev_close = float(hist.Close.iloc[-2]) if len(hist) > 1 else current_price
        return {
            "ticker": ticker,
            "current_price": round(current_price, 2) if current_price else None,
            "previous_close": round(prev_close, 2) if prev_close else current_price,
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "market_cap": info.get("marketCap"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
        }
    except Exception as e:
        print(f"yfinance error: {str(e)[:80]}")
    
    # Fallback: direct Yahoo chart API (often works when yfinance is rate-limited)
    if requests is not None:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            data = r.json()
            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            prices = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            prices = [p for p in prices if p is not None]
            current_price = prices[-1] if prices else meta.get("regularMarketPrice")
            prev_close = prices[-2] if len(prices) > 1 else current_price
            if current_price:
                return {
                    "ticker": ticker,
                    "current_price": round(float(current_price), 2),
                    "previous_close": round(float(prev_close), 2) if prev_close else round(float(current_price), 2),
                    "pe_ratio": None,
                    "market_cap": None,
                    "52_week_high": meta.get("fiftyTwoWeekHigh"),
                    "52_week_low": meta.get("fiftyTwoWeekLow"),
                    "avg_volume": None,
                    "_source": "yahoo_chart_api",
                }
        except Exception as e:
            print(f"Chart API fallback error: {str(e)[:80]}")
    
    return {"_error": "All Yahoo Finance endpoints unavailable"}


def fetch_crypto_coingecko(crypto_id: str) -> dict | None:
    if requests is None:
        return None
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={crypto_id}"
        r = requests.get(url, timeout=20)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            d = data[0]
            return {
                "current_price": d.get("current_price"),
                "market_cap": d.get("market_cap"),
                "total_volume": d.get("total_volume"),
                "price_change_24h": d.get("price_change_24h"),
                "price_change_percentage_24h": d.get("price_change_percentage_24h"),
                "ath": d.get("ath"),
                "ath_change_percentage": d.get("ath_change_percentage"),
            }
        return None
    except Exception as e:
        return {"_error": str(e)}


def _calc_rsi(prices: list, period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _calc_sma(prices: list, period: int) -> float | None:
    if len(prices) >= period:
        return round(sum(prices[-period:]) / period, 2)
    return None


def _fetch_yahoo_news(ticker: str) -> list:
    if requests is None:
        return []
    try:
        import xml.etree.ElementTree as ET
        url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        news = []
        for item in items[:5]:
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
    except Exception as e:
        return [{"_error": str(e)}]


def _analyze_sentiment(news_items: list) -> dict:
    if not news_items:
        return {"score": 0, "label": "NEUTRAL", "mentions": 0}
    bullish_words = {"surge", "rally", "gain", "beat", "strong", "bull", "buy", "upgrade", "outperform", "growth", "breakout", "moon", "rocket", " ath", "all-time high"}
    bearish_words = {"drop", "fall", "crash", "bear", "sell", "downgrade", "underperform", "loss", "miss", "weak", "recession", "layoff", "lawsuit", "sec", "investigation"}
    bullish = 0
    bearish = 0
    for item in news_items:
        title = item.get("title", "").lower()
        for w in bullish_words:
            if w in title:
                bullish += 1
        for w in bearish_words:
            if w in title:
                bearish += 1
    total = bullish + bearish
    if total == 0:
        return {"score": 0, "label": "NEUTRAL", "mentions": 0}
    score = round((bullish - bearish) / total * 100, 1)
    label = "BULLISH" if score > 20 else "BEARISH" if score < -20 else "NEUTRAL"
    return {"score": score, "label": label, "bullish_mentions": bullish, "bearish_mentions": bearish, "total_mentions": total}


def _generate_empty_result(task_id: str, subject: str, ticker: str, asset_type: str, reason: str) -> dict:
    return {
        "task_id": task_id,
        "subject": subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommendation": "NO_DATA",
        "confidence": 0,
        "summary": f"Data unavailable for {ticker}: {reason}. No recommendation can be made.",
        "key_metrics": {"ticker": ticker, "_error": reason},
        "sources": [],
        "full_text": f"## {ticker} Research — DATA UNAVAILABLE\n\nReason: {reason}\n\nNo real-time data was retrieved. The system refuses to fabricate numbers.\n",
        "paper_trade_signal": "NO_DATA",
        "paper_trade_price": 0,
        "asset_type": asset_type,
    }


def _generate_recommendation(metrics: dict, asset_type: str, sentiment: dict) -> tuple:
    pe = metrics.get("pe_ratio")
    rsi = metrics.get("rsi_14")
    change = metrics.get("price_change_24h", 0) or metrics.get("price_change_percentage_24h", 0)
    sentiment_label = sentiment.get("label", "NEUTRAL")
    sentiment_score = sentiment.get("score", 0)

    if asset_type == "crypto":
        if change and change > 5:
            rec, conf = "HOLD", 65
        elif change and change < -8:
            rec, conf = "ACCUMULATE", 60
        else:
            rec, conf = "WATCH", 55
    else:
        if pe and pe > 40:
            rec, conf = "HOLD", 58
        elif pe and pe < 20:
            rec, conf = "BUY", 72
        elif rsi and rsi > 70:
            rec, conf = "SELL", 65
        elif rsi and rsi < 30:
            rec, conf = "BUY", 70
        else:
            rec, conf = "HOLD", 55

    if sentiment_label == "BULLISH" and sentiment_score > 30:
        conf = min(95, conf + 10)
        if rec == "HOLD":
            rec = "ACCUMULATE"
    elif sentiment_label == "BEARISH" and sentiment_score < -30:
        conf = max(30, conf - 15)
        if rec in ("BUY", "ACCUMULATE"):
            rec = "HOLD"

    return rec, conf


def run(args) -> bool:
    task_id = args.task_id
    subject = args.subject
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    ticker, asset_type, crypto_id = infer_ticker(subject)
    
    real_data = None
    if asset_type == "crypto":
        real_data = fetch_crypto_coingecko(crypto_id) if crypto_id else None
    else:
        real_data = fetch_stock_yfinance(ticker)
    
    if real_data is None or real_data.get("_error"):
        reason = real_data.get("_error", "No data source available") if real_data else "No data source available"
        result = _generate_empty_result(task_id, subject, ticker, asset_type, reason)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"EMPTY result for {output_path} — {reason}")
        return True
    
    metrics = real_data
    metrics["ticker"] = ticker
    
    # Calculate RSI and SMA from history
    if asset_type == "stock" and yf is not None:
        try:
            hist = yf.Ticker(ticker).history(period="1mo")
            if len(hist) > 14:
                prices = hist.Close.tolist()
                metrics["rsi_14"] = _calc_rsi(prices)
                metrics["sma_20"] = _calc_sma(prices, 20)
                metrics["sma_50"] = _calc_sma(prices, 50)
                if len(prices) >= 5:
                    metrics["price_change_5d_pct"] = round((prices[-1] - prices[-5]) / prices[-5] * 100, 2)
        except Exception:
            pass
    
    news = _fetch_yahoo_news(ticker)
    sentiment = _analyze_sentiment(news)
    metrics["sentiment_score"] = sentiment.get("score")
    metrics["sentiment_label"] = sentiment.get("label")
    
    price = metrics.get("current_price", 0) or 0
    recommendation, confidence = _generate_recommendation(metrics, asset_type, sentiment)
    
    result = {
        "task_id": task_id,
        "subject": subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommendation": recommendation,
        "confidence": confidence,
        "summary": f"{ticker} — {sentiment.get('label', 'NEUTRAL')} sentiment, {recommendation} ({confidence}% confidence). "
                   + f"PE: {metrics.get('pe_ratio', 'N/A')}, RSI: {metrics.get('rsi_14', 'N/A')}, Price: ${price}.",
        "key_metrics": metrics,
        "news": news[:3] if news else [],
        "sentiment": sentiment,
        "sources": ["https://finance.yahoo.com/quote/" + ticker if asset_type == "stock" else "https://www.coingecko.com/en/coins/" + crypto_id],
        "full_text": (
            f"## {ticker} Research Result\n\n"
            f"### Recommendation: {recommendation} ({confidence}% confidence)\n\n"
            f"### Sentiment: {sentiment.get('label', 'NEUTRAL')} ({sentiment.get('score', 0)})\n\n"
            f"### Key Metrics\n" + "\n".join([f"- **{k}:** {v}" for k, v in metrics.items()]) + "\n\n"
            f"### Latest News\n" + "\n".join([f"- [{n.get('title', '')}]({n.get('url', '')})" for n in news[:3]])
        ),
        "paper_trade_signal": recommendation,
        "paper_trade_price": price,
        "asset_type": asset_type,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    print(f"REAL result for {output_path} — {ticker} {recommendation} {confidence}%")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock/Crypto Research Bot")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--details", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    success = run(args)
    sys.exit(0 if success else 1)

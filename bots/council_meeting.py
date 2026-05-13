"""
bots/council_meeting.py
War room where all specialist bots cast votes on a ticker.
Produces a consensus recommendation, weighted by historical accuracy.
Usage:
  python bots/council_meeting.py --ticker NVDA \
    --research dashboard/data/output/20260513-001.json \
    --earnings dashboard/data/earnings/NVDA.json \
    --model dashboard/data/models/NVDA.json \
    --kyc dashboard/data/kyc/NVDA.json \
    --advisor dashboard/data/advisor_notes/NVDA.json \
    --output dashboard/data/council/20260513-NVDA.json \
    [--memo-dir docs/COUNCIL_MEMOS]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "dashboard" / "data" / "bot_registry.json"

# ── Config ─────────────────────────────────────────────────────────

STRONG_CONSENSUS_THRESHOLD = 75.0
LOW_CONSENSUS_THRESHOLD = 60.0
SIZE_BOOST_STRONG_CONSENSUS = 0.25  # +25% position size


# ── Load helpers ───────────────────────────────────────────────────

def _load(path: str) -> dict:
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"bots": {}}


def _get_bot_weight(name: str, registry: dict) -> float:
    """Weight = historical_accuracy / 100, minimum 0.3."""
    bot = registry["bots"].get(name, {})
    acc = bot.get("historical_accuracy", 50.0)
    total = bot.get("total_predictions", 0)
    # New bots get a small grace weight
    if total < 5:
        return 0.5
    return max(0.3, acc / 100.0)


# ── Vote logic ─────────────────────────────────────────────────────

RECOMMENDATION_ORDER = ["BUY", "ACCUMULATE", "HOLD", "WATCH", "SELL"]
REC_SCORES = {"BUY": 2, "ACCUMULATE": 1.5, "HOLD": 0, "WATCH": -0.5, "SELL": -2}


def _extract_recommendation(data: dict, fallback: str = "HOLD") -> tuple:
    """Try to pull recommendation + confidence from a bot output dict."""
    rec = data.get("recommendation", data.get("signal", fallback))
    conf = data.get("confidence", data.get("score", 50))
    return str(rec).upper(), int(conf) if isinstance(conf, (int, float)) else 50


def _bot_vote(bot_name: str, bot_data: dict, registry: dict) -> dict:
    """Each specialist votes based on its own data."""
    rec, conf = _extract_recommendation(bot_data, fallback="HOLD")
    weight = _get_bot_weight(bot_name, registry)
    return {
        "bot": bot_name,
        "recommendation": rec,
        "confidence": conf,
        "weight": round(weight, 2),
        "weight_reason": f"{bot_name} accuracy={registry['bots'].get(bot_name,{}).get('historical_accuracy',50)}%",
    }


def _compute_consensus(votes: list) -> tuple:
    """
    Weighted voting. Returns (consensus_rec, consensus_score, vote_breakdown).
    consensus_score = weighted agreement around the winning recommendation.
    """
    if not votes:
        return "HOLD", 0, {}

    # Accumulate weighted votes
    weighted = {}
    total_weight = 0.0
    for v in votes:
        rec = v["recommendation"]
        w = v["weight"] if v["confidence"] >= 45 else v["weight"] * 0.5  # damp low-confidence bots
        weighted[rec] = weighted.get(rec, 0) + w
        total_weight += w

    # Pick winner
    winner = max(weighted, key=weighted.get)
    winner_weight = weighted[winner]
    consensus_score = round(winner_weight / total_weight * 100, 1) if total_weight > 0 else 0

    # Normalize breakdown
    breakdown = {k: round(v / total_weight * 100, 1) if total_weight > 0 else 0 for k, v in weighted.items()}

    return winner, consensus_score, breakdown


def _write_memo(ticker: str, date_str: str, votes: list, consensus_rec: str, consensus_score: float, memo_dir: Path):
    """If consensus is low, write a markdown memo explaining the disagreement."""
    memo_dir.mkdir(parents=True, exist_ok=True)
    path = memo_dir / f"{date_str}-{ticker}.md"

    lines = [
        f"# Council Memo: {ticker} — {date_str}",
        "",
        f"**Consensus:** {consensus_rec} ({consensus_score}% agreement)",
        "",
        "## Vote Breakdown",
        "",
        "| Bot | Vote | Confidence | Weight |",
        "|-----|------|------------|--------|",
    ]
    for v in votes:
        lines.append(f"| {v['bot']} | {v['recommendation']} | {v['confidence']}% | {v['weight']} |")

    lines += [
        "",
        "## Disagreement Analysis",
        "",
    ]

    buy_votes = [v for v in votes if v["recommendation"] in ("BUY", "ACCUMULATE")]
    sell_votes = [v for v in votes if v["recommendation"] == "SELL"]
    hold_votes = [v for v in votes if v["recommendation"] in ("HOLD", "WATCH")]

    if buy_votes and sell_votes:
        lines.append(f"**Polarized:** {len(buy_votes)} bullish vs {len(sell_votes)} bearish. High uncertainty.")
    elif consensus_score < LOW_CONSENSUS_THRESHOLD:
        lines.append("Consensus is weak. No dominant view. Recommend additional research or reduced position size.")
    else:
        lines.append("Mild disagreement. Majority view holds but minority flags risks to monitor.")

    lines += ["", "---", "", "*Memo auto-generated by Council Meeting bot.*"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


# ── Main ─────────────────────────────────────────────────────────────

def run_council(ticker: str, research: dict, earnings: dict, model: dict,
                kyc: dict, advisor: dict, portfolio: dict,
                output_path: str, memo_dir: str = None) -> dict:

    registry = _load_registry()
    ticker = ticker.upper()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Cast votes
    votes = []
    votes.append(_bot_vote("researcher_bot", research, registry))
    votes.append(_bot_vote("earnings_analyzer", earnings, registry))
    votes.append(_bot_vote("financial_model", model, registry))
    votes.append(_bot_vote("kyc_screen", kyc, registry))
    votes.append(_bot_vote("advisor_reasoning", advisor, registry))
    votes.append(_bot_vote("portfolio_constructor", portfolio, registry))

    # Compute consensus
    consensus_rec, consensus_score, breakdown = _compute_consensus(votes)

    # Position sizing adjustment
    trade_boost = 0.0
    if consensus_score >= STRONG_CONSENSUS_THRESHOLD:
        trade_boost = SIZE_BOOST_STRONG_CONSENSUS
        verdict = "STRONG CONSENSUS"
    elif consensus_score >= LOW_CONSENSUS_THRESHOLD:
        verdict = "MILD CONSENSUS"
    else:
        verdict = "WEAK CONSENSUS"

    # Write memo if weak
    memo_path = None
    if consensus_score < LOW_CONSENSUS_THRESHOLD and memo_dir:
        memo_path = _write_memo(ticker, date_str, votes, consensus_rec, consensus_score, Path(memo_dir))

    result = {
        "ticker": ticker,
        "date": date_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "consensus": {
            "recommendation": consensus_rec,
            "confidence": consensus_score,
            "verdict": verdict,
            "position_size_boost_pct": trade_boost,
        },
        "votes": votes,
        "breakdown": breakdown,
        "memo_path": memo_path,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Council: {ticker} => {consensus_rec} ({consensus_score}% {verdict})")
    if memo_path:
        print(f"  Memo written: {memo_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Council Meeting — bot war room")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--research", default="")
    parser.add_argument("--earnings", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--kyc", default="")
    parser.add_argument("--advisor", default="")
    parser.add_argument("--portfolio", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--memo-dir", default="")

    args = parser.parse_args()

    data = {
        "research": _load(args.research),
        "earnings": _load(args.earnings),
        "model": _load(args.model),
        "kyc": _load(args.kyc),
        "advisor": _load(args.advisor),
        "portfolio": _load(args.portfolio),
    }

    run_council(
        ticker=args.ticker,
        research=data["research"],
        earnings=data["earnings"],
        model=data["model"],
        kyc=data["kyc"],
        advisor=data["advisor"],
        portfolio=data["portfolio"],
        output_path=args.output,
        memo_dir=args.memo_dir or None,
    )


if __name__ == "__main__":
    main()

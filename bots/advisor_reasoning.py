"""
bots/advisor_reasoning.py
Generates narrative: why we made this call.
Usage: called by orchestrator after all analyses complete.
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path


def generate_reasoning(research: dict, earnings: dict, model: dict, pitchbook_path: str) -> dict:
    ticker = _extract_ticker(research.get("subject", ""))
    rec = research.get("recommendation", "HOLD")
    conf = research.get("confidence", 0)
    summary = research.get("summary", "")
    metrics = research.get("key_metrics", {})
    
    e_score = earnings.get("earnings_catalyst_score", 0)
    e_verdict = earnings.get("verdict", "")
    m_target = model.get("blended_target", "N/A")
    m_mos = model.get("margin_of_safety_pct", 0)
    m_verdict = model.get("verdict", "")
    
    reasons = []
    if rec == "BUY":
        reasons.append(f"We see a buying opportunity in {ticker}.")
    elif rec == "ACCUMULATE":
        reasons.append(f"{ticker} looks attractive on a scale-in basis.")
    elif rec == "HOLD":
        reasons.append(f"We maintain our HOLD on {ticker}.")
    elif rec == "SELL":
        reasons.append(f"We are downgrading {ticker} to SELL.")
    else:
        reasons.append(f"We are watching {ticker} closely.")
    
    reasons.append(f"")
    reasons.append(f"**Research Findings:**")
    reasons.append(f"- {summary}")
    
    reasons.append(f"")
    reasons.append(f"**Earnings Analysis:**")
    reasons.append(f"- {e_verdict} — catalyst score {e_score}/100")
    
    reasons.append(f"")
    reasons.append(f"**Valuation Model:**")
    reasons.append(f"- {m_verdict} with a blended target of ${m_target}")
    if m_mos > 10:
        reasons.append(f"- **Margin of safety:** {m_mos}% — favorable downside protection")
    
    reasons.append(f"")
    reasons.append(f"**Confidence Drivers:**")
    reasons.append(f"- Overall confidence: **{conf}%**")
    
    if metrics:
        m_pe = metrics.get("pe_ratio", metrics.get("trailing_pe"))
        if m_pe:
            reasons.append(f"- P/E ratio of {m_pe} vs peers")
        m_rsi = metrics.get("rsi_14")
        if m_rsi:
            reasons.append(f"- RSI(14) at {m_rsi} — {'oversold' if m_rsi < 30 else 'overbought' if m_rsi > 70 else 'neutral'}")
    
    reasons.append(f"")
    reasons.append(f"**Risks to the Thesis:**")
    if m_mos < 5:
        reasons.append(f"- Limited margin of safety — downside risk elevated")
    if conf < 60:
        reasons.append(f"- Low confidence indicates significant uncertainty")
    reasons.append(f"- Market-wide macro risks (rates, geopolitics)")
    reasons.append(f"- Stock-specific execution risk")
    
    reasons.append(f"")
    reasons.append(f"**Why This Strategy:**")
    if conf > 75 and m_mos > 15:
        reasons.append(f"This is a **QUALITY** play: high conviction, strong valuation, proven fundamentals.")
    elif e_score > 60:
        reasons.append(f"This is a **MOMENTUM** play: earnings acceleration driving the thesis.")
    elif m_mos > 15:
        reasons.append(f"This is a **VALUE** play: mispriced asset with significant upside.")
    else:
        reasons.append(f"This is a **GROWTH** play: positioned for forward-looking appreciation.")
    
    reasoning = "\n".join(reasons)
    
    return {
        "ticker": ticker,
        "recommendation": rec,
        "confidence": conf,
        "reasoning": reasoning,
        "pitchbook_path": pitchbook_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confidence_factors": {
            "earnings_score": e_score,
            "valuation_margin": m_mos,
            "research_confidence": conf,
        }
    }


def run(args) -> bool:
    def _load(path):
        p = Path(path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    research = _load(args.research)
    earnings = _load(args.earnings)
    model = _load(args.model)
    
    data = generate_reasoning(research, earnings, model, args.pitchbook)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"Advisor reasoning for {data['ticker']}: {data['recommendation']} ({data['confidence']}%)")
    return True


def _extract_ticker(subject: str) -> str:
    import re
    m = re.search(r'\b([A-Z]{2,5})\b', subject)
    return m.group(1) if m else ""


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--research", required=True)
    p.add_argument("--earnings", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--pitchbook", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

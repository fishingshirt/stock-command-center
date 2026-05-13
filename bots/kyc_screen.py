"""
bots/kyc_screen.py
Compliance screening: sanctions, PEP, ESG.
Usage: python bots/kyc_screen.py --ticker NVDA --output dashboard/data/kyc/NVDA.json
"""
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
import random

def screen(ticker: str) -> dict:
    """Mock compliance screening — realistic scores."""
    sanctions_risk = random.uniform(0, 10)  # 0 = clean, 10 = severe
    pep_exposure = 0  # Public companies rarely have PEP founders
    esg_score = random.uniform(40, 85)  # 0-100
    controversy_count = random.randint(0, 3)
    jurisdiction_risk = "low"
    if random.random() < 0.05:
        jurisdiction_risk = "medium"
    if random.random() < 0.01:
        jurisdiction_risk = "high"
    
    overall_score = 100 - sanctions_risk * 5 - controversy_count * 10
    if esg_score < 40:
        overall_score -= 15
    overall_score = max(0, min(100, overall_score))
    
    risk_level = "LOW" if overall_score > 80 else "MEDIUM" if overall_score > 50 else "HIGH"
    
    flags = []
    if sanctions_risk > 3:
        flags.append(f"Elevated sanctions exposure ({round(sanctions_risk, 1)}/10)")
    if esg_score < 50:
        flags.append(f"Poor ESG score ({round(esg_score, 1)})")
    if controversy_count > 0:
        flags.append(f"{controversy_count} active controversies")
    if jurisdiction_risk != "low":
        flags.append(f"Jurisdiction risk: {jurisdiction_risk}")
    
    return {
        "ticker": ticker.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compliance_score": round(overall_score, 1),
        "risk_level": risk_level,
        "sanctions_risk": round(sanctions_risk, 1),
        "pep_exposure": pep_exposure,
        "esg_score": round(esg_score, 1),
        "controversy_count": controversy_count,
        "jurisdiction_risk": jurisdiction_risk,
        "flags": flags,
        "pass": risk_level != "HIGH"
    }


def run(args) -> bool:
    ticker = args.ticker.upper()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = screen(ticker)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"KYC for {ticker}: {data['risk_level']} risk | Score {data['compliance_score']}/100 | {'PASS' if data['pass'] else 'FAIL'}")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    sys.exit(0 if run(args) else 1)

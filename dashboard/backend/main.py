"""
dashboard/backend/main.py
FastAPI backend for Stock Command Center.
"""
import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from whiteboard.parser import load_board

_env_root = os.environ.get("SCC_REPO_ROOT")
if _env_root:
    REPO_ROOT = Path(_env_root)
else:
    REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Container fallback if path resolves to root
if str(REPO_ROOT) == "/" and Path("/app/dashboard").exists():
    REPO_ROOT = Path("/app")
OUTPUT_DIR = REPO_ROOT / "dashboard" / "data" / "output"
LOG_DIR = REPO_ROOT / "logs"
BOARD_PATH = REPO_ROOT / "whiteboard" / "kanban.md"

app = FastAPI(title="Stock Command Center API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TriggerCycleResponse(BaseModel):
    status: str
    message: str


def _load_all_results() -> list:
    results = []
    if not OUTPUT_DIR.exists():
        return results
    for p in sorted(OUTPUT_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append(data)
        except Exception:
            continue
    return results


def _latest_run_info() -> dict:
    latest_time = None
    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.glob("*.json"))
        if files:
            latest_time = datetime.fromtimestamp(max(f.stat().st_mtime for f in files)).isoformat()
    return {
        "status": "ok",
        "last_cycle": latest_time or "never",
        "output_count": len(list(OUTPUT_DIR.glob("*.json"))) if OUTPUT_DIR.exists() else 0,
    }


@app.get("/health")
def health():
    return _latest_run_info()


@app.get("/api/recommendations")
def list_recommendations():
    return _load_all_results()


@app.get("/api/recommendations/{ticker}")
def get_recommendation(ticker: str):
    for rec in _load_all_results():
        if ticker.upper() in rec.get("subject", "").upper():
            return rec
    raise HTTPException(status_code=404, detail="Ticker not found")


@app.get("/api/sectors")
def list_sectors():
    counts = {"stocks": 0, "crypto": 0, "other": 0}
    for rec in _load_all_results():
        asset = rec.get("asset_type", "other")
        if asset in counts:
            counts[asset] += 1
        else:
            counts["other"] += 1
    return {"sectors": counts}


@app.get("/api/feed")
def feed(limit: int = 20):
    logs = []
    if LOG_DIR.exists():
        log_file = LOG_DIR / "orchestrator.log"
        if log_file.exists():
            with open(log_file, "r", errors="ignore") as f:
                lines = f.readlines()
            for line in reversed(lines[-limit:]):
                line = line.strip()
                if line:
                    logs.append(line)
    return {"entries": logs}


@app.get("/api/archive")
def archive(page: int = 1, per_page: int = 10):
    all_results = _load_all_results()
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": all_results[start:end],
        "page": page,
        "per_page": per_page,
        "total": len(all_results),
    }


@app.get("/api/whiteboard")
def whiteboard():
    if not BOARD_PATH.exists():
        return {"error": "Whiteboard not found"}
    return load_board(str(BOARD_PATH))


@app.post("/api/trigger-cycle", response_model=TriggerCycleResponse)
def trigger_cycle():
    import subprocess
    try:
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "bots" / "run_cycle.py")],
            capture_output=True,
            text=True,
            timeout=900,
        )
        status = "ok" if proc.returncode == 0 else "error"
        return {"status": status, "message": (proc.stdout + proc.stderr)[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# === ADVISOR API ===

@app.get("/api/pitchbooks")
def list_pitchbooks():
    pb_dir = REPO_ROOT / "dashboard" / "data" / "pitchbooks"
    import json as _json
    pitchbooks = []
    if pb_dir.exists():
        for md_file in sorted(pb_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            ticker = md_file.stem
            reason_file = REPO_ROOT / "dashboard" / "data" / "advisor_notes" / f"{ticker}.json"
            model_file = REPO_ROOT / "dashboard" / "data" / "models" / f"{ticker}.json"
            kyc_file = REPO_ROOT / "dashboard" / "data" / "kyc" / f"{ticker}.json"
            
            pb_data = {"ticker": ticker, "content": "", "recommendation": "HOLD", "confidence": 0, "strategy": "GROWTH", "margin_of_safety": 0, "model_target": "N/A", "dcf_target": "N/A", "comps_target": "N/A", "kyc_risk": "UNKNOWN", "compliance_score": 0, "summary": ""}
            
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                pb_data["content"] = content
                lines = content.split("\n")
                for line in lines[:10]:
                    if "**Recommendation:**" in line:
                        pb_data["recommendation"] = line.split("**Recommendation:**")[-1].strip()
                    if "**Confidence:**" in line:
                        try:
                            pb_data["confidence"] = int(line.split("**Confidence:**")[-1].strip().replace("%", ""))
                        except:
                            pass
                    if "**Strategy:**" in line:
                        pb_data["strategy"] = line.split("**Strategy:**")[-1].strip()
                for line in lines:
                    if "**Executive Summary**" in line or "## 1. Executive Summary" in line:
                        idx = lines.index(line) + 2
                        pb_data["summary"] = lines[idx].strip() if idx < len(lines) else ""
                        break
            except Exception:
                pass
            
            if model_file.exists():
                try:
                    with open(model_file, "r", encoding="utf-8") as f:
                        m = _json.load(f)
                    pb_data["model_target"] = m.get("blended_target", "N/A")
                    pb_data["margin_of_safety"] = m.get("margin_of_safety_pct", 0)
                    pb_data["dcf_target"] = m.get("dcf_model", {}).get("intrinsic_per_share", "N/A")
                    pb_data["comps_target"] = m.get("comparable_model", {}).get("implied_price_pe", "N/A")
                except Exception:
                    pass
            
            if kyc_file.exists():
                try:
                    with open(kyc_file, "r", encoding="utf-8") as f:
                        k = _json.load(f)
                    pb_data["kyc_risk"] = k.get("risk_level", "UNKNOWN")
                    pb_data["compliance_score"] = k.get("compliance_score", 0)
                except Exception:
                    pass
            
            pitchbooks.append(pb_data)
    return {"pitchbooks": pitchbooks}


@app.get("/api/pitchbooks/{ticker}")
def get_pitchbook(ticker: str):
    pb_file = REPO_ROOT / "dashboard" / "data" / "pitchbooks" / f"{ticker}.md"
    if not pb_file.exists():
        raise HTTPException(status_code=404, detail="Pitchbook not found")
    with open(pb_file, "r", encoding="utf-8") as f:
        return {"ticker": ticker.upper(), "content": f.read()}


@app.get("/api/strategies")
def strategy_leaderboard():
    sys.path.insert(0, str(REPO_ROOT))
    from bots.strategy_tracker import get_leaderboard
    return {"strategy_stats": get_leaderboard()}


@app.get("/api/earnings/{ticker}")
def get_earnings(ticker: str):
    e_file = REPO_ROOT / "dashboard" / "data" / "earnings" / f"{ticker}.json"
    if not e_file.exists():
        raise HTTPException(status_code=404, detail="Earnings data not found")
    with open(e_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/models/{ticker}")
def get_model(ticker: str):
    m_file = REPO_ROOT / "dashboard" / "data" / "models" / f"{ticker}.json"
    if not m_file.exists():
        raise HTTPException(status_code=404, detail="Model not found")
    with open(m_file, "r", encoding="utf-8") as f:
        return json.load(f)


# === COUNCIL API ===

@app.get("/api/council")
def list_council():
    council_dir = REPO_ROOT / "dashboard" / "data" / "council"
    results = []
    if council_dir.exists():
        for p in sorted(council_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(data)
            except Exception:
                continue
    return {"councils": results}


@app.get("/api/council/{ticker}")
def get_council(ticker: str):
    council_dir = REPO_ROOT / "dashboard" / "data" / "council"
    if council_dir.exists():
        for p in sorted(council_dir.glob(f"*-{ticker}.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    raise HTTPException(status_code=404, detail="Council record not found")


@app.get("/api/feedback")
def feedback_report():
    fb_path = REPO_ROOT / "dashboard" / "data" / "feedback_report.json"
    if fb_path.exists():
        with open(fb_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"message": "No feedback report yet"}


# === BOT LEADERBOARD ===

@app.get("/api/bot_leaderboard")
def bot_leaderboard():
    reg_path = REPO_ROOT / "dashboard" / "data" / "bot_registry.json"
    if reg_path.exists():
        with open(reg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bots = list(data.get("bots", {}).values())
        bots.sort(key=lambda b: b.get("historical_accuracy", 0), reverse=True)
        return {"bots": bots}
    return {"bots": []}


# === PORTFOLIO API ===

@app.get("/api/portfolio")
def portfolio():
    sys.path.insert(0, str(REPO_ROOT))
    from bots.paper_trade import get_stats
    return get_stats()


# === BOT STATUS / WAR ROOM API ===

@app.get("/api/bots/status")
def bots_status():
    """Live status of all worker bots: last run, accuracy, active."""
    reg_path = REPO_ROOT / "dashboard" / "data" / "bot_registry.json"
    bots = []
    if reg_path.exists():
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, bot in data.get("bots", {}).items():
                last_run = bot.get("last_run", "never")
                is_active = False
                if last_run != "never":
                    try:
                        from datetime import datetime, timezone
                        lr = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        age_hours = (datetime.now(timezone.utc) - lr).total_seconds() / 3600
                        is_active = age_hours < 1
                    except Exception:
                        pass
                bots.append({
                    "name": name,
                    "expertise": bot.get("expertise", ""),
                    "accuracy": bot.get("historical_accuracy", 0),
                    "predictions": bot.get("total_predictions", 0),
                    "avg_confidence": bot.get("avg_confidence", 0),
                    "last_run": last_run,
                    "active": is_active,
                })
        except Exception:
            pass
    
    # Add orchestrator status from log
    log_file = LOG_DIR / "orchestrator.log"
    last_cycle = "never"
    if log_file.exists():
        try:
            with open(log_file, "r", errors="ignore") as f:
                lines = f.readlines()
            for line in reversed(lines):
                if "=== Cycle complete ===" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        last_cycle = " ".join(parts[:2])
                    break
        except Exception:
            pass
    
    return {
        "bots": sorted(bots, key=lambda b: b["accuracy"], reverse=True),
        "orchestrator_last_cycle": last_cycle,
        "total_bots": len(bots),
        "active_bots": sum(1 for b in bots if b["active"]),
    }
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

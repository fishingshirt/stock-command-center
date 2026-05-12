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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

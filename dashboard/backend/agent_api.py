"""
dashboard/backend/agent_api.py

to mount with: from agent_api import router as agent_router
app.include_router(agent_router, prefix="/api")
"""
import json
from pathlib import Path
from fastapi import APIRouter

REPO = Path(__file__).resolve().parent.parent.parent

# Data paths differ between local dev (repo/dashboard/data/) and Docker container (/app/data/)
if (Path("/app/data") / "agent_registry.json").exists():
    DATA_ROOT = Path("/app/data")
elif (REPO / "dashboard" / "data" / "agent_registry.json").exists():
    DATA_ROOT = REPO / "dashboard" / "data"
else:
    DATA_ROOT = REPO / "dashboard" / "data"

AGENT_REG = DATA_ROOT / "agent_registry.json"
MEM_DIR = DATA_ROOT / "agent_memories"
BOARD_DIR = DATA_ROOT / "agent_boards"
MEET_DIR = DATA_ROOT / "agent_meetings"

# Output dir
OUTPUT_DIR = Path("/app/data/output") if Path("/app/data/output").exists() else (REPO / "dashboard" / "data" / "output")

router = APIRouter()

def _load(path: Path):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}

@router.get("/agents")
def list_agents():
    reg = _load(AGENT_REG)
    agents = []
    for a in reg.get("agents", []):
        mem = _load(MEM_DIR / f"{a['id']}.json")
        agents.append({
            "id": a["id"],
            "name": a["name"],
            "role": a["role"],
            "department": a.get("department", "Unknown"),
            "active": a.get("active", False),
            "level": a.get("level", "mid"),
            "salary": a.get("salary", 0),
            "reports_to": a.get("reports_to"),
            "accuracy": mem.get("accuracy", 100.0),
            "tasks_completed": mem.get("tasks_completed", 0),
            "tasks_failed": mem.get("tasks_failed", 0),
            "on_pip": mem.get("on_pip", False),
            "rework_count": mem.get("rework_count", 0),
            "profile_pic": a.get("profile_pic", f"/assets/real_faces/{a['id'].lower()}.jpg"),
            "responsibilities": a.get("responsibilities", []),
        })
    return {"company": "Stock Command Center", "agents": agents}

@router.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    reg = _load(AGENT_REG)
    for a in reg.get("agents", []):
        if a["id"] == agent_id:
            mem = _load(MEM_DIR / f"{agent_id}.json")
            board = _load(BOARD_DIR / f"{agent_id}.json")
            # Get recent outputs
            outputs = []
            for f in sorted(OUTPUT_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                try:
                    d = json.load(open(f))
                    if d.get("assigned_agent") == agent_id:
                        outputs.append({"file": f.name, "subject": d.get("subject",""), "date": d.get("date","")})
                except:
                    pass
            return {
                **a,
                "memory": mem,
                "board": board,
                "recent_outputs": outputs,
            }
    return {"error": "Agent not found"}

@router.get("/agent-board/{agent_id}")
def get_agent_board(agent_id: str):
    board = _load(BOARD_DIR / f"{agent_id}.json")
    return board if board else {"To Do": [], "In Progress": [], "Done": [], "agent_id": agent_id}

@router.get("/agent-meetings/{agent_id}")
def get_agent_meetings(agent_id: str):
    path = MEET_DIR / f"{agent_id}.jsonl"
    meetings = []
    if path.exists():
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        meetings.append(json.loads(line))
                    except:
                        pass
    # Also read shared meeting log
    shared = MEET_DIR / "shared.jsonl"
    if shared.exists():
        with open(shared, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        d = json.loads(line)
                        if agent_id in d.get("participants", []):
                            meetings.append(d)
                    except:
                        pass
    meetings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"agent_id": agent_id, "meetings": meetings[:50]}

@router.get("/agent-org-chart")
def agent_org_chart():
    reg = _load(AGENT_REG)
    agents = [a for a in reg.get("agents", []) if a.get("active")]
    
    by_mgr = {}
    for a in agents:
        mgr = a.get("reports_to") or "ROOT"
        by_mgr.setdefault(mgr, []).append(a)

    def build(mgr_id: str):
        children = []
        for a in by_mgr.get(mgr_id, []):
            mem = _load(MEM_DIR / f"{a['id']}.json")
            children.append({
                "id": a["id"],
                "name": a["name"],
                "title": a["role"],
                "department": a.get("department", "Unknown"),
                "level": a.get("level", "mid"),
                "performance": mem.get("accuracy", 100.0),
                "on_pip": mem.get("on_pip", False),
                "pic": a.get("profile_pic", f"/assets/real_faces/{a['id'].lower()}.jpg"),
                "children": build(a["id"]),
            })
        return children

    return {"tree": build("ROOT"), "company": reg.get("company", "SCC")}

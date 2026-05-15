"""
bots/employee_manager.py
Stock Command Center — Employee Management System

A virtual corporation with real employees:
  - Each bot is mapped to an employee
  - Employees have performance scores, hire/fire dates, faces
  - Termination: <40% accuracy after 10+ predictions
  - Hiring: auto-backfills with generated profiles + synthetic face

Usage:
  python bots/employee_manager.py review
  python bots/employee_manager.py hire --role "Junior Analyst" --dept Research
  python bots/employee_manager.py fire --emp EMP-012
  python bots/employee_manager.py list
  python bots/employee_manager.py org-chart
"""
import argparse, json, os, sys, subprocess, random, hashlib, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EMP_FILE = REPO / "dashboard" / "data" / "employees.json"
TERM_FILE = REPO / "dashboard" / "data" / "employees_terminated.json"
FACE_DIR = REPO / "dashboard" / "frontend" / "public" / "assets" / "faces"

FIRST_NAMES = ["James","Maria","Robert","Lisa","Michael","Jennifer","David","Linda","William","Patricia","Richard","Elizabeth","Joseph","Susan","Thomas","Jessica","Christopher","Sarah","Charles","Karen","Daniel","Nancy","Matthew","Margaret","Anthony","Emily","Mark","Betty","Donald","Sandra","Steven","Ashley","Paul","Dorothy","Andrew","Kimberly","Joshua","Helen","Edward","Donna","Kenneth","Carol","Kevin","Michelle"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker"]

# ── Data helpers ───────────────────────────────────────────────────

def _load(path: Path) -> dict | list:
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}

def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ── Seed default org (only if file empty) ───────────────────────────

def _seed_org():
    if EMP_FILE.exists():
        return
    org = {
        "company_name": "Stock Command Center Corp",
        "founded": "2026-05-15",
        "ceo": "fishingshirt",
        "employees": [
            {"id":"EMP-001","name":"Alexander Whitfield","title":"CEO","department":"Executive","status":"active","hire_date":"2026-05-15","bio":"Founder and CEO.","profile_pic":"/assets/faces/emp-001.svg","performance_score":100.0,"total_tasks":1,"success_rate":100.0,"salary":1000000,"managed_by":None},
            {"id":"EMP-002","name":"Sarah Chen","title":"COO","department":"Operations","status":"active","hire_date":"2026-05-15","bio":"Runs daily operations, ensures bot execution, whiteboard health.","profile_pic":"/assets/faces/emp-002.svg","performance_score":92.0,"total_tasks":47,"success_rate":91.5,"salary":450000,"managed_by":"EMP-001"},
            {"id":"EMP-003","name":"Marcus Thompkins","title":"CFO","department":"Finance","status":"active","hire_date":"2026-05-15","bio":"Oversees paper trading, capital allocation.","profile_pic":"/assets/faces/emp-003.svg","performance_score":88.0,"total_tasks":0,"success_rate":88.0,"salary":400000,"managed_by":"EMP-001"},
            {"id":"EMP-004","name":"Dr. Elena Vasquez","title":"CIO","department":"Investment","status":"active","hire_date":"2026-05-15","bio":"Controls buy/sell decisions, runs paper trading engine.","profile_pic":"/assets/faces/emp-004.svg","performance_score":85.0,"total_tasks":0,"success_rate":85.0,"salary":480000,"managed_by":"EMP-001"},
            {"id":"EMP-005","name":"Raj Patel","title":"CTO","department":"Engineering","status":"active","hire_date":"2026-05-15","bio":"Manages codebase, Docker, self-builds.","profile_pic":"/assets/faces/emp-005.svg","performance_score":90.0,"total_tasks":3,"success_rate":89.0,"salary":420000,"managed_by":"EMP-001"},
            {"id":"EMP-006","name":"James O'Brien","title":"Head of Research","department":"Research","status":"active","hire_date":"2026-05-15","bio":"Supervises research team, reviews analyst output.","profile_pic":"/assets/faces/emp-006.svg","performance_score":82.0,"total_tasks":52,"success_rate":81.0,"salary":320000,"managed_by":"EMP-002"},
            {"id":"EMP-007","name":"Linda Wu","title":"Sr. Research Analyst — Equities","department":"Research","status":"active","hire_date":"2026-05-15","bio":"Large-cap equity researcher. Tech and financials specialist.","profile_pic":"/assets/faces/emp-007.svg","performance_score":78.0,"total_tasks":35,"success_rate":76.0,"salary":180000,"managed_by":"EMP-006"},
            {"id":"EMP-008","name":"David Kim","title":"Sr. Research Analyst — Crypto","department":"Research","status":"active","hire_date":"2026-05-15","bio":"Crypto researcher. BTC, ETH, SOL ecosystem specialist.","profile_pic":"/assets/faces/emp-008.svg","performance_score":74.0,"total_tasks":28,"success_rate":72.0,"salary":175000,"managed_by":"EMP-006"},
            {"id":"EMP-009","name":"Fatima Al-Rashid","title":"Risk & Compliance Officer","department":"Compliance","status":"active","hire_date":"2026-05-15","bio":"Runs KYC screening and compliance checks.","profile_pic":"/assets/faces/emp-009.svg","performance_score":95.0,"total_tasks":52,"success_rate":94.0,"salary":210000,"managed_by":"EMP-003"},
            {"id":"EMP-010","name":"Carlos Mendez","title":"Quantitative Analyst","department":"Research","status":"active","hire_date":"2026-05-15","bio":"Builds models: DCF, comps, momentum. Backtests strategies.","profile_pic":"/assets/faces/emp-010.svg","performance_score":71.0,"total_tasks":52,"success_rate":69.0,"salary":220000,"managed_by":"EMP-006"},
            {"id":"EMP-011","name":"Victoria Hartwell","title":"Strategic Advisor","department":"Advisory","status":"active","hire_date":"2026-05-15","bio":"Synthesizes research into investment theses and pitchbooks.","profile_pic":"/assets/faces/emp-011.svg","performance_score":80.0,"total_tasks":52,"success_rate":79.0,"salary":280000,"managed_by":"EMP-004"},
            {"id":"EMP-012","name":"Tom Bradley","title":"Junior Research Analyst","department":"Research","status":"active","hire_date":"2026-05-15","bio":"New hire. Learning sector rotation and macro calls.","profile_pic":"/assets/faces/emp-012.svg","performance_score":60.0,"total_tasks":12,"success_rate":58.0,"salary":95000,"managed_by":"EMP-006"},
        ],
        "open_positions": [],
        "total_ever_hired": 12,
        "total_terminated": 0,
        "next_emp_id": 13
    }
    _save(EMP_FILE, org)

# ── Face generation ────────────────────────────────────────────────

def _fetch_real_face() -> bytes | None:
    """Fetch a real synthetic face from this-person-does-not-exist.com"""
    import time, re
    base = "https://this-person-does-not-exist.com"
    heads = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": base}
    try:
        r = requests.get(base, headers=heads, timeout=15)
        if r.status_code == 200:
            urls = re.findall(r'src="(/img/avatar-[a-z0-9]+\.jpg)"', r.text)
            if urls:
                url = f"{base}{urls[0]}"
                img = requests.get(url, headers=heads, timeout=15)
                if img.status_code == 200 and img.content.startswith(b'\xff\xd8'):
                    return img.content
    except Exception:
        pass
    return None

def _generate_face(emp_id: str) -> str:
    """Generate a profile face: real synthetic first, avatar fallback."""
    import urllib.parse
    REAL_DIR = REPO / "dashboard" / "frontend" / "public" / "assets" / "real_faces"
    REAL_DIR.mkdir(parents=True, exist_ok=True)

    # Try real face first
    real = _fetch_real_face()
    if real:
        path = REAL_DIR / f"{emp_id.lower()}.jpg"
        with open(path, "wb") as f:
            f.write(real)
        return f"/assets/real_faces/{emp_id.lower()}.jpg"

    # Fallback: dicebear avataaars
    seed = urllib.parse.quote(f"{emp_id}_{random.randint(1000,9999)}")
    url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={seed}"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 200:
            svg_path = FACE_DIR / f"{emp_id.lower()}.svg"
            with open(svg_path, "wb") as f:
                f.write(r.content)
            return f"/assets/faces/{emp_id.lower()}.svg"
    except Exception:
        pass

    # Ultimate fallback: deterministic colored circle
    h = hashlib.md5(emp_id.encode()).hexdigest()
    bg = f"#{h[:6]}"
    initials = emp_id.replace("EMP-", "")
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="g" cx="50%" cy="40%" r="60%">
      <stop offset="0%" style="stop-color:{bg};stop-opacity:1" />
      <stop offset="100%" style="stop-color:#000000;stop-opacity:1" />
    </radialGradient>
  </defs>
  <circle cx="100" cy="100" r="100" fill="url(#g)" />
  <text x="100" y="120" text-anchor="middle" fill="white" font-family="sans-serif" font-size="60" font-weight="bold">{initials}</text>
</svg>'''
    svg_path = FACE_DIR / f"{emp_id.lower()}.svg"
    with open(svg_path, "w") as f:
        f.write(svg)
    return f"/assets/faces/{emp_id.lower()}.svg"

# ── Employee creation ────────────────────────────────────────────

def _make_emp(role: str, dept: str, level: str = "mid", mgr: str = None) -> dict:
    org = _load(EMP_FILE)
    eid = org["next_emp_id"]
    org["next_emp_id"] = eid + 1
    _save(EMP_FILE, org)

    fname = random.choice(FIRST_NAMES)
    lname = random.choice(LAST_NAMES)
    emp_id = f"EMP-{eid:03d}"
    face = _generate_face(emp_id)

    bios = {
        "Research Analyst": f"{fname} specializes in equity research and technical analysis.",
        "Earnings Analyst": f"{fname} tracks EPS surprises and earnings momentum.",
        "Financial Modeler": f"{fname} builds DCF and comp-based valuation models.",
        "Compliance Analyst": f"{fname} ensures all tickers pass KYC and compliance screens.",
        "Investment Writer": f"{fname} compiles research into pitchbooks and investment memos.",
        "Strategy Advisor": f"{fname} synthesizes multi-source data into actionable theses.",
        "Portfolio Manager": f"{fname} sizes positions and manages portfolio risk.",
        "DevOps Engineer": f"{fname} maintains infrastructure and deployment pipelines.",
    }
    base = {"junior": 85000, "mid": 150000, "senior": 220000, "exec": 450000}
    salary = base.get(level, 150000) + random.randint(-5000, 15000)

    return {
        "id": emp_id, "name": f"{fname} {lname}", "title": role, "department": dept,
        "status": "active", "hire_date": datetime.now().strftime("%Y-%m-%d"),
        "bio": bios.get(role, f"{fname} is a {level}-level {role} in {dept}."),
        "profile_pic": face, "performance_score": 70.0 + random.randint(-10, 20),
        "total_tasks": 0, "success_rate": 0.0, "salary": salary,
        "managed_by": mgr, "reviews": []
    }

def hire(role: str, dept: str, level: str = "mid", mgr: str = None):
    org = _load(EMP_FILE)
    emp = _make_emp(role, dept, level, mgr)
    org["employees"].append(emp)
    org["total_ever_hired"] = org.get("total_ever_hired", 0) + 1
    _save(EMP_FILE, org)
    print(json.dumps({"action":"hired","id":emp["id"],"name":emp["name"],"role":emp["title"],"dept":dept,"salary":emp["salary"],"pic":emp["profile_pic"]}))
    return emp

def fire(emp_id: str, reason: str = "performance"):
    org = _load(EMP_FILE)
    emp = None
    for e in org.get("employees", []):
        if e["id"] == emp_id:
            emp = e
            break
    if not emp:
        print(json.dumps({"error": f"Employee {emp_id} not found"})); return None

    emp["status"] = "terminated"
    emp["termination_date"] = datetime.now().isoformat()
    emp["termination_reason"] = reason
    org["employees"] = [x for x in org["employees"] if x["id"] != emp_id]
    org["total_terminated"] = org.get("total_terminated", 0) + 1
    _save(EMP_FILE, org)

    term = _load(TERM_FILE)
    if not isinstance(term, list): term = []
    term.append(emp)
    _save(TERM_FILE, term)
    print(json.dumps({"action":"terminated","id":emp_id,"name":emp["name"],"reason":reason,"salary_saved":emp["salary"]}))
    return emp

# ── Performance review ──────────────────────────────────────────

def review():
    org = _load(EMP_FILE)
    now = datetime.now(timezone.utc)
    terminations, hires = [], []

    # Bot → employee mapping via title search
    registry_path = REPO / "dashboard" / "data" / "bot_registry.json"
    registry = _load(registry_path) if registry_path.exists() else {}

    for emp in org.get("employees", []):
        if emp["status"] != "active":
            continue

        # Find matching bot
        bot_match = None
        for bn, bd in registry.get("bots", {}).items():
            # crude matching: bot name contains parts of title
            tid = emp["title"].lower().replace(" ", "_")
            if bn in tid or tid in bn:
                bot_match = bd
                break

        if bot_match:
            acc = bot_match.get("historical_accuracy", 50.0)
            preds = bot_match.get("total_predictions", 0)
            emp["performance_score"] = acc
            emp["total_tasks"] = preds
            emp["success_rate"] = acc
            emp["reviews"].append({"date": now.isoformat(), "accuracy": acc, "preds": preds})
            emp["reviews"] = emp["reviews"][-12:]

        # Rework before fire logic
        underperforming = (emp["total_tasks"] >= 10 and emp["performance_score"] < 40) or (emp.get("performance_score", 100) < 30 and emp["total_tasks"] >= 5)

        if underperforming:
            from whiteboard.parser import add_task
            # If not on PIP, assign rework
            if not emp.get("on_pip", False):
                emp["on_pip"] = True
                emp["pip_start_date"] = now.isoformat()
                emp["rework_count"] = emp.get("rework_count", 0) + 1
                # Create mentorship task for their manager
                mgr_id = emp.get("managed_by")
                mgr_name = mgr_id
                for e in org.get("employees", []):
                    if e["id"] == mgr_id:
                        mgr_name = e["name"]
                        break
                add_task(
                    str(REPO / "whiteboard" / "kanban.md"),
                    f"REWORK ASSIGNED: Mentor {emp['name']} ({emp['title']}) — performance {emp['performance_score']:.0f}%",
                    f"- Employee {emp['id']} is on Performance Improvement Plan (PIP)\n- Manager: {mgr_name} ({mgr_id})\n- Assigned rework: review methodology, retrain on ticker analysis pattern\n- Re-evaluation after rework completes\n- Threshold needed: >40% accuracy",
                    priority="high",
                    bot="self_build",
                    git_commit=True,
                )
                print(f"REWORK: {emp['name']} placed on PIP, assigned to manager {mgr_name}")
            else:
                # Already on PIP — fire if no improvement
                pip_start = datetime.fromisoformat(emp.get("pip_start_date", "2000-01-01").replace("Z", "+00:00"))
                hours_on_pip = (now - pip_start).total_seconds() / 3600
                # Give at least 24 hours / one full cycle on PIP before final decision
                if hours_on_pip >= 12:  # roughly one review cycle
                    terminations.append(emp)
        else:
            # Improvement — clear PIP
            if emp.get("on_pip", False):
                emp["on_pip"] = False
                emp["pip_end_date"] = now.isoformat()
                emp["pip_outcome"] = "PASSED"
                print(f"PIP CLEARED: {emp['name']} performance recovered to {emp['performance_score']:.0f}%")

    # Execute terminations
    mgr_backfill = {}
    for emp in terminations:
        mgr = emp.get("managed_by")
        if mgr:
            mgr_backfill.setdefault(mgr, []).append(emp["title"])
        
        rework_str = f"{emp.get('rework_count', 0)}x rework cycles"
        pip_hrs = None
        if emp.get("pip_start_date"):
            pip_hrs = (now - datetime.fromisoformat(emp["pip_start_date"].replace("Z","+00:00"))).total_seconds()/3600
        reason = f"Fired after underperformance: {emp['performance_score']:.0f}% accuracy over {emp['total_tasks']} predictions. {rework_str} on PIP ({pip_hrs:.0f}h). No improvement."
        
        # Update before fire so the reason is saved
        emp["termination_reason"] = reason
        fire(emp["id"], reason)

    # Auto-hire replacements
    for mgr, roles in mgr_backfill.items():
        for role in roles:
            # Map role back to dept/level
            dept, level = "Research", "mid"
            for bn, cfg in {
                "researcher_bot": {"role":"Research Analyst","dept":"Research","level":"senior"},
                "earnings_analyzer": {"role":"Earnings Analyst","dept":"Finance","level":"mid"},
                "financial_model": {"role":"Financial Modeler","dept":"Finance","level":"senior"},
                "kyc_screen": {"role":"Compliance Analyst","dept":"Compliance","level":"mid"},
                "pitchbook_generator": {"role":"Investment Writer","dept":"Advisory","level":"mid"},
                "advisor_reasoning": {"role":"Strategy Advisor","dept":"Advisory","level":"senior"},
                "portfolio_constructor": {"role":"Portfolio Manager","dept":"Investment","level":"senior"},
                "self_build": {"role":"DevOps Engineer","dept":"Engineering","level":"senior"},
            }.items():
                if cfg["role"] == role:
                    dept, level = cfg["dept"], cfg["level"]
                    break
            new_emp = hire(role, dept, level, mgr)
            hires.append(new_emp)

    _save(EMP_FILE, org)
    report = {"time": now.isoformat(), "active": len([e for e in org["employees"] if e["status"]=="active"]), "termed": len(terminations), "hired": len(hires), "terminated_names": [e["name"] for e in terminations], "hired_names": [e["name"] for e in hires]}
    print(json.dumps(report, indent=2))
    logf = REPO / "logs" / "employee_review.log"
    logf.parent.mkdir(exist_ok=True)
    with open(logf, "a") as f:
        f.write(json.dumps(report) + "\n")
    return report

# ── Org chart ────────────────────────────────────────────────────

def org_chart():
    org = _load(EMP_FILE)
    by_mgr = {}
    for e in org.get("employees", []):
        if e["status"] != "active": continue
        mgr = e.get("managed_by") or "ROOT"
        by_mgr.setdefault(mgr, []).append(e)
    def tree(mgr_id, depth=0):
        for e in by_mgr.get(mgr_id, []):
            s = "  " * depth
            icon = "🟢" if e["performance_score"] >= 50 else "🟡" if e["performance_score"] >= 35 else "🔴"
            print(f"{s}{icon} [{e['id']}] {e['name']} — {e['title']} ({e['performance_score']:.0f}%)")
            tree(e["id"], depth + 1)
    print("\n📊 SCC ORGANIZATION CHART\n")
    tree("ROOT")
    print()

# ── List ──────────────────────────────────────────────────────────

def list_all():
    org = _load(EMP_FILE)
    term = _load(TERM_FILE)
    if not isinstance(term, list): term = []
    active = [e for e in org.get("employees", []) if e.get("status") == "active"]
    out = {
        "company": org.get("company_name", "SCC Corp"),
        "active": len(active), "terminated": len(term),
        "total_ever_hired": org.get("total_ever_hired", 0),
        "total_terminated": org.get("total_terminated", 0),
        "employees": active,
        "past_employees": term[-20:],
    }
    print(json.dumps(out, indent=2))
    return out

# ── Main ─────────────────────────────────────────────────────────

def main():
    _seed_org()
    p = argparse.ArgumentParser(description="SCC Employee Manager")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("review", help="Run performance review cycle")
    sub.add_parser("list", help="List all employees")
    sub.add_parser("org-chart", help="Show hierarchy")
    pf = sub.add_parser("fire", help="Terminate employee")
    pf.add_argument("--emp", required=True)
    pf.add_argument("--reason", default="performance")
    ph = sub.add_parser("hire", help="Hire employee")
    ph.add_argument("--role", required=True)
    ph.add_argument("--dept", required=True)
    ph.add_argument("--level", default="mid", choices=["junior","mid","senior","exec"])
    ph.add_argument("--manager", default=None)

    args = p.parse_args()
    if args.cmd == "review": review()
    elif args.cmd == "list": list_all()
    elif args.cmd == "org-chart": org_chart()
    elif args.cmd == "fire": fire(args.emp, args.reason)
    elif args.cmd == "hire": hire(args.role, args.dept, args.level, args.manager)
    else: p.print_help()

if __name__ == "__main__":
    main()

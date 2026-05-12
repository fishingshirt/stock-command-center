"""
whiteboard/parser.py
Read and write the kanban.md whiteboard file.
"""
import re
import os
import subprocess
from datetime import datetime
from typing import Optional

SECTION_ORDER = ["To Do", "In Progress", "Done"]

def _parse_board(content: str) -> dict:
    board = {"To Do": [], "In Progress": [], "Done": [], "raw": content}
    # Split by ## section headers
    parts = re.split(r'\n##\s+', content)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        header_match = re.match(r'(To Do|In Progress|Done)', part, re.IGNORECASE)
        if not header_match:
            continue
        section = header_match.group(1).title()
        if section == "In Progress":
            section = "In Progress"
        body = part[header_match.end():].strip()
        # Extract tasks
        tasks = list(_extract_tasks(body))
        board[section] = tasks
    return board

def _extract_tasks(text: str) -> list:
    # Match ### Task ID: ... blocks
    pattern = r'###\s+Task\s+ID:\s+(\S+)(.*?)(?=###\s+Task\s+ID:|\Z)'
    for m in re.finditer(pattern, text, re.DOTALL):
        task_id = m.group(1).strip()
        body = m.group(2).strip()
        task = {"task_id": task_id, "raw": body}
        # Extract key fields
        for key in ("Subject", "Assigned Bot", "Priority", "Created", "Completed At", "Started At", "Result", "Summary"):
            field_re = rf'\*\*{key}:\*\*\s*(.+)'
            fm = re.search(field_re, body, re.IGNORECASE)
            if fm:
                task[key.lower().replace(" ", "_")] = fm.group(1).strip()
        # Extract Details block
        details_match = re.search(r'\*\*Details:\*\*\s*\n(.*?)(?=###|\Z)', body, re.DOTALL)
        if details_match:
            task["details"] = details_match.group(1).strip()
        else:
            task["details"] = ""
        yield task

def load_board(path: str = "whiteboard/kanban.md") -> dict:
    """Load and parse the kanban board. Returns dict with sections."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return _parse_board(content)

def _get_latest_id(board: dict) -> int:
    """Find highest NNN for current date prefix."""
    prefix = datetime.now().strftime("%Y%m%d")
    max_num = 0
    for section in SECTION_ORDER:
        for task in board.get(section, []):
            tid = task.get("task_id", "")
            if tid.startswith(prefix + "-"):
                try:
                    num = int(tid.split("-")[-1])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
    return max_num

def _board_to_text(board: dict) -> str:
    """Serialize board dict back to markdown."""
    lines = ["# Stock Command Center — Whiteboard", "", "This is the single source of truth for all research and build tasks. Do not edit outside the three sections below.", "", "---", ""]
    for section in SECTION_ORDER:
        lines.append(f"## {section}")
        lines.append("")
        tasks = board.get(section, [])
        if not tasks:
            lines.append("_(No tasks in this section.)_")
            lines.append("")
        else:
            for task in tasks:
                task_id = task.get("task_id", "UNKNOWN")
                lines.append(f"### Task ID: {task_id}")
                for key in ["Subject", "Assigned Bot", "Priority", "Created", "Started At", "Completed At", "Result", "Summary"]:
                    val = task.get(key.lower().replace(" ", "_"))
                    if val:
                        lines.append(f"**{key}:** {val}")
                details = task.get("details", "")
                if details:
                    lines.append("**Details:**")
                    lines.append(details)
                lines.append("")
    return "\n".join(lines)

def move_task(path: str, task_id: str, from_section: str, to_section: str, extra_fields: Optional[dict] = None, git_commit: bool = True) -> bool:
    """Move a task between sections and optionally add fields. Returns success."""
    board = load_board(path)
    task = None
    for t in board.get(from_section, []):
        if t.get("task_id") == task_id:
            task = t
            break
    if not task:
        print(f"[parser] Task {task_id} not found in {from_section}")
        return False
    board[from_section].remove(task)
    if extra_fields:
        task.update(extra_fields)
    board[to_section].append(task)
    text = _board_to_text(board)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if git_commit:
        _git_push(path, f"task({task_id}): move {from_section} → {to_section}")
    return True

def add_task(path: str, subject: str, details: str, priority: str = "medium", bot: str = "researcher_bot", git_commit: bool = True) -> str:
    """Add a new task to To Do and return its ID."""
    board = load_board(path)
    latest = _get_latest_id(board)
    prefix = datetime.now().strftime("%Y%m%d")
    new_id = f"{prefix}-{latest + 1:03d}"
    task = {
        "task_id": new_id,
        "subject": subject,
        "assigned_bot": bot,
        "priority": priority,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "details": details,
    }
    board["To Do"].append(task)
    text = _board_to_text(board)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if git_commit:
        _git_push(path, f"task({new_id}): add {subject}")
    return new_id

def _git_push(path: str, message: str):
    """Git add, commit, and push the whiteboard file."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    try:
        subprocess.run(["git", "-C", repo_root, "add", "whiteboard/kanban.md"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", repo_root, "commit", "-m", message], check=False, capture_output=True, text=True)
        subprocess.run(["git", "-C", repo_root, "push", "origin", "main"], check=False, capture_output=True, text=True)
    except Exception as e:
        print(f"[parser] Git push warning: {e}")

if __name__ == "__main__":
    import json
    b = load_board()
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in b.items() if k != "raw"}, indent=2))

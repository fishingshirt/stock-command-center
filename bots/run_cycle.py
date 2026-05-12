"""
bots/run_cycle.py
Entry point called by cron. Wraps orchestrator + handles lock file.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bots.main_orchestrator import run_cycle

if __name__ == "__main__":
    run_cycle()

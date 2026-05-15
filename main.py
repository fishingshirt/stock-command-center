"""
ASGI entry point for uvicorn.
Re-exports the FastAPI app from dashboard.backend.main.
"""
import os, sys
from pathlib import Path

# Ensure the repo root is on the path
_repo_root = os.environ.get("SCC_REPO_ROOT", str(Path(__file__).resolve().parent))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dashboard.backend.main import app

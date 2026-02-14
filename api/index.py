"""Vercel serverless entrypoint delegating to the canonical FastAPI app."""

from __future__ import annotations

import sys
from pathlib import Path

# Keep project root importable in serverless runtime.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.server import app  # noqa: E402,F401

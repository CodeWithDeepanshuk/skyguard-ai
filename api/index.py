"""Vercel serverless ASGI entrypoint for SkyGuard AI."""

import sys
from pathlib import Path

# Ensure repository root and src/ are on sys.path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skyguard.api.app import create_app

# Export ASGI application for Vercel Python runtime
app = create_app(root=ROOT)

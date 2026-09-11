"""Start the offline SkyGuard API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


if __name__ == "__main__":
    runtime_dir = ROOT / "data" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("SKYGUARD_HOST", "127.0.0.1")
    port = int(os.environ.get("SKYGUARD_PORT", "8000"))
    uvicorn.run("skyguard.api.app:create_app", factory=True, host=host, port=port, reload=False)

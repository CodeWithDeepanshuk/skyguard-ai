"""Fail a Render build early when deploy-critical SkyGuard assets are missing."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    required = [
        ROOT / "dashboard" / "index.html",
        ROOT / "config" / "all_india_aws_network.csv",
        ROOT / "data" / "demo" / "packet_errors.csv.gz",
        ROOT / "models" / "phase10_final.joblib",
        ROOT / "reports" / "qc_baseline.json",
        ROOT / "reports" / "phase10_final.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Render build is missing required assets: {', '.join(missing)}")

    from skyguard.api.app import create_app

    app = create_app(ROOT, ":memory:")
    # Hidden dashboard routes are intentionally absent from OpenAPI, while the
    # FastAPI included-router compatibility object has no direct ``path``.
    paths = set(app.openapi()["paths"])
    paths.update(filter(None, (getattr(route, "path", None) for route in app.routes)))
    required_routes = {"/", "/health", "/api/live/status", "/api/v1/network/status"}
    missing_routes = sorted(required_routes - paths)
    app.state.runtime.store.close()
    if missing_routes:
        raise SystemExit(f"Render build is missing required routes: {', '.join(missing_routes)}")

    print(json.dumps({
        "status": "render_build_ready",
        "python": sys.version.split()[0],
        "required_assets": len(required),
        "required_routes": sorted(required_routes),
    }))


if __name__ == "__main__":
    main()

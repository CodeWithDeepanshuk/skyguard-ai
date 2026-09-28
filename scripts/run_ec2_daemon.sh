#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR/src:${PYTHONPATH:-}"
export RENDER_URL="${RENDER_URL:-https://skyguard-ai-wbm9.onrender.com}"
export SKYGUARD_INGESTION_TOKEN="${SKYGUARD_INGESTION_TOKEN:-sih26073_secure_token_2026}"
export DATABASE_URL="${DATABASE_URL:-postgresql://skyguard_db_user:OHoTCrHQU7LYMX8zUSzmfGP06zBrrta0@dpg-dasf6m0473hc7381lk9g-a.singapore-postgres.render.com/skyguard_db}"

echo "[SkyGuard EC2 Ingestion Daemon Starting]"
echo "Render URL: $RENDER_URL"
echo "Polling cadence: every 15 minutes (900 seconds)"

exec python3 -m skyguard.ingestion.worker \
    --providers IMD_API \
    --loop \
    --interval-seconds 900 \
    --forward-to-render "$RENDER_URL" \
    --token "$SKYGUARD_INGESTION_TOKEN"

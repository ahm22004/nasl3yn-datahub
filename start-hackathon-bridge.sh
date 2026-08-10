#!/usr/bin/env bash
# Hackathon Discovery Bridge Launcher
# Usage: ./start-hackathon-bridge.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load env if exists
if [[ -f "hackathon_bridge.env" ]]; then
    export $(grep -v '^#' hackathon_bridge.env | xargs)
fi

# Defaults
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8888}"

echo "Starting Hackathon Discovery Bridge..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Proxy: ${HACKATHON_SCRAPER_PROXY:-none}"
echo "  Cache TTL: ${SCAN_CACHE_TTL_SECONDS:-3600}s"
echo "  Reports: ${REPORTS_DIR:-~/.hermes/reports/hackathons}"

# Check dependencies
command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
command -v uv >/dev/null || { echo "uv not found (install: curl -LsSf https://astral.sh/uv/install.sh | sh)"; exit 1; }

# Run with uv (fast, isolated)
exec uv run uvicorn hackathon_bridge:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info
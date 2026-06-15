#!/usr/bin/env bash
# SignalSmith AI — Linux/macOS startup
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — edit Splunk credentials before continuing."
fi

# Load ports from .env for display
WEB_PORT=$(grep -E '^SPLUNK_WEB_PORT=' .env 2>/dev/null | cut -d= -f2 || echo "8005")
API_SCHEME=$(grep -E '^SPLUNK_API_SCHEME=' .env 2>/dev/null | cut -d= -f2 || echo "https")
API_PORT=$(grep -E '^SPLUNK_API_PORT=' .env 2>/dev/null | cut -d= -f2 || echo "8090")

echo "==> Building frontend..."
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then npm install; fi
npm run build

echo "==> Starting backend (UI + API on port 8080)..."
cd "$ROOT/backend"
pip install -q -r requirements.txt
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
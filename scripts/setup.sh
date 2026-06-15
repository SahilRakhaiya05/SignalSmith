#!/usr/bin/env bash
# SignalSmith AI — install dependencies
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit Splunk credentials."
fi

echo "==> Python dependencies"
python3 -m pip install -r backend/requirements.txt

echo "==> Frontend dependencies"
cd frontend && npm install

echo ""
echo "Setup complete."
echo "  1. Edit .env with Splunk + MCP credentials (see docs/SPLUNK_SETUP.md)"
echo "  2. ./scripts/start.sh"
echo "  3. Open http://localhost:8080"
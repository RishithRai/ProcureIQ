#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env || ! -x .venv/bin/uvicorn ]]; then
  echo 'Install Python dependencies and configure the local .env first.' >&2
  exit 1
fi
for port in 8000 5173; do
  if lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null; then
    echo "Port $port is already in use. Stop the existing ProcureIQ development server before using this launcher." >&2
    exit 1
  fi
done
set -a
source .env
set +a
.venv/bin/uvicorn procureiq.api.app:create_app --factory --host 127.0.0.1 --port 8000 &
api_pid=$!
(cd apps/web && exec ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort) &
web_pid=$!
trap 'kill "$api_pid" "$web_pid" 2>/dev/null || true; wait || true' EXIT INT TERM
wait

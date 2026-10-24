#!/usr/bin/env bash
# Run the browser suite (F0.11) against the local stack, started in its test mode.
#
#   scripts/e2e.sh                     every flow and corpus case, Chromium
#   scripts/e2e.sh -k receipt          only what matches, as pytest's -k
#   scripts/e2e.sh --browser webkit    Safari's engine
#
# Screenshots land in backend/e2e-results/screens/; a failed test keeps its trace in
# backend/e2e-results/traces/ (open with: uv run playwright show-trace <file>).
# Put the usual stack back with `docker compose up -d backend` afterwards.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --wait backend frontend postgres minio >/dev/null
for _ in $(seq 1 60); do
  curl -sf http://localhost:8000/health >/dev/null && curl -sf http://localhost:5173/ >/dev/null && break
  sleep 1
done

cd backend
E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:5173}" \
E2E_API_URL="${E2E_API_URL:-http://localhost:8000}" \
  uv run pytest tests/e2e -p no:cacheprovider --tracing retain-on-failure \
  --output e2e-results/traces "$@"

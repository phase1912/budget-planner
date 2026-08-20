#!/usr/bin/env bash
# Regenerate src/api/schema.ts from the backend's current OpenAPI schema (F9.3.2).
#
# Exports the schema via the backend's own script rather than a running server,
# so this works offline and needs no backend process listening on a port.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run --project ../backend python ../backend/scripts/export_openapi_schema.py > openapi.json
npx openapi-typescript openapi.json -o src/api/schema.ts
rm openapi.json

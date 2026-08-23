#!/usr/bin/env python
"""Export the FastAPI OpenAPI schema for frontend codegen (F9.3.1).

The single source the frontend's generated types (F9.3.2) and its CI drift
check (F9.3.3) both read from. Builds the schema by introspecting routes and
Pydantic models only — no environment variables and no database connection
are required, so this runs identically on a laptop and in CI.

Usage:
    uv run python scripts/export_openapi_schema.py > openapi.json
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://dummy:dummy@localhost/dummy"
os.environ["ANTHROPIC_API_KEY"] = "dummy"

from app.main import create_app


def build_schema() -> dict[str, Any]:
    """Return the app's OpenAPI schema, built from route/model introspection alone."""
    return create_app().openapi()


def main() -> None:
    """Write the app's OpenAPI schema as JSON to stdout."""
    json.dump(build_schema(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

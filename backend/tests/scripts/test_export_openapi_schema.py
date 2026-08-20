"""Guards for the OpenAPI export script the frontend codegen depends on (F9.3.1).

The frontend's generated types (F9.3.2) and its CI drift check (F9.3.3) both trust
that this script's output is a valid, importable OpenAPI document built without any
runtime configuration — these tests guard exactly that contract.
"""

import os

import pytest

from scripts.export_openapi_schema import build_schema


def test_schema_export_needs_no_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Schema generation is route/model introspection, not a running service.

    A contributor with no `.env` file, and CI with no secrets configured, must
    still be able to regenerate the frontend's types.
    """
    for key in list(os.environ):
        if key.lower() in {"database_url", "anthropic_api_key"}:
            monkeypatch.delenv(key, raising=False)

    schema = build_schema()

    assert schema["openapi"].startswith("3.")


def test_schema_exposes_every_registered_route() -> None:
    schema = build_schema()

    assert "/health" in schema["paths"]
    assert "/version" in schema["paths"]

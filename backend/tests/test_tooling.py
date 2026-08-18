"""Guards for the ruff/mypy/pre-commit tooling contract (F0.1.3).

No business behaviour is asserted here — there is none yet. These guard the one
thing this task delivers: ruff and mypy are pinned dev dependencies with mypy in
strict mode, and the pre-commit config wires both plus the whitespace/EOF fixers
the task requires, so a change that quietly drops one of them fails the suite
instead of only being noticed in review.
"""

import tomllib
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text())


def test_ruff_and_mypy_are_pinned_dev_dependencies() -> None:
    """Both tools must be resolvable, lockfile-pinned deps, not ambient installs."""
    dev_deps = " ".join(_pyproject()["dependency-groups"]["dev"])
    assert "ruff" in dev_deps
    assert "mypy" in dev_deps


def test_mypy_runs_in_strict_mode() -> None:
    assert _pyproject()["tool"]["mypy"]["strict"] is True


def test_pre_commit_config_wires_ruff_mypy_and_the_required_fixers() -> None:
    """The task requires ruff (lint+format), mypy, and the whitespace/EOF fixers."""
    config_text = (REPO_ROOT / ".pre-commit-config.yaml").read_text()
    required_hooks = (
        "trailing-whitespace",
        "end-of-file-fixer",
        "ruff-check",
        "ruff-format",
        "mypy",
    )
    for hook_id in required_hooks:
        assert f"id: {hook_id}" in config_text

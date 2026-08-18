"""Guards for the repo-wide conventions delivered by F0.1.4.

No business behaviour is asserted here — there is none yet. These guard the three
things this task delivers: an .editorconfig covering both languages, a LICENSE, and
a CONTRIBUTING.md that states the branch naming and commit message conventions used
by the ticket workflow — so a change that quietly drops one of them fails the suite
instead of only being noticed in review.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_editorconfig_covers_python_and_typescript() -> None:
    config_text = (REPO_ROOT / ".editorconfig").read_text()
    assert "root = true" in config_text
    assert "[*.py]" in config_text
    assert "[*.{ts,tsx,js,jsx,json,css}]" in config_text


def test_license_file_exists() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text()
    assert "MIT License" in license_text


def test_contributing_states_branch_naming_and_commit_conventions() -> None:
    contributing_text = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    assert "task/<backlog-key-with-dashes>-<short-slug>" in contributing_text
    assert "Co-Authored-By" in contributing_text
    assert "Closes #42" in contributing_text

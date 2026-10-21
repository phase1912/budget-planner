"""The assistant's tools (F21.7, ADR-0028): one module per thing the user keeps.

Every module here is imported on first use, and every tool class in it registers itself:
adding a tool is adding a class, in a new module or an existing one.
"""

import importlib
import pkgutil

from app.assistant.tools.base import CARDS, REGISTRY, Tool, Writer

_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return
    for module in pkgutil.iter_modules(__path__):
        if module.name not in {"base", "toolbox"}:
            importlib.import_module(f"{__name__}.{module.name}")
    _loaded = True


def all_tools() -> dict[str, Tool]:
    """Every tool, by name."""
    _load()
    return REGISTRY


def card_writers() -> dict[str, Writer]:
    """Every writer, by the kind of card it proposes."""
    _load()
    return CARDS

"""
Build strategy abstraction layer.

Provides :func:`get_strategy` to obtain the right :class:`BuildStrategy`
implementation for a given ``build_system`` identifier.
"""

from __future__ import annotations

from .base import BuildStrategy
from .cmake_strategy import CMakeStrategy
from .custom_script_strategy import CustomScriptStrategy

STRATEGY_REGISTRY: dict[str, type[BuildStrategy]] = {
    "cmake": CMakeStrategy,
    "custom_script": CustomScriptStrategy,
}

STRATEGY_LABELS: dict[str, str] = {
    "cmake": "CMake",
    "custom_script": "Custom Script",
}


def get_strategy(build_system: str) -> BuildStrategy:
    """Return an instance of the strategy for *build_system*."""
    cls = STRATEGY_REGISTRY.get(build_system)
    if cls is None:
        raise ValueError(f"Unknown build system: {build_system!r}")
    return cls()

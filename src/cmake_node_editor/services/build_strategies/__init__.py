"""
Build strategy registry — **single source of truth** for all build systems.

To add a new build system:

1. Create ``my_strategy.py`` in this package with a :class:`BuildStrategy`
   subclass.
2. Create a matching form widget in ``dialogs/widgets/`` that implements
   ``load_from_node(node)`` / ``apply_to_node(node)``.
3. Import your strategy class here and append it to ``_STRATEGY_CLASSES``.

That's it — all dialogs, the command builder, and the worker will pick it
up automatically.
"""

from __future__ import annotations

from .base import BuildStrategy
from .cmake_strategy import CMakeStrategy
from .custom_script_strategy import CustomScriptStrategy

# -------------------------------------------------------------------
# Registration: add new strategy classes here
# -------------------------------------------------------------------
_STRATEGY_CLASSES: list[type[BuildStrategy]] = [
    CMakeStrategy,
    CustomScriptStrategy,
]

# -------------------------------------------------------------------
# Derived look-ups (populated once at import time)
# -------------------------------------------------------------------
_INSTANCES: dict[str, BuildStrategy] = {}

for _cls in _STRATEGY_CLASSES:
    _inst = _cls()
    _INSTANCES[_inst.name] = _inst

# Ordered list of strategy names (same order as _STRATEGY_CLASSES)
STRATEGY_NAMES: list[str] = list(_INSTANCES.keys())

# name → human-readable label
STRATEGY_LABELS: dict[str, str] = {k: v.label for k, v in _INSTANCES.items()}


def get_strategy(build_system: str) -> BuildStrategy:
    """Return the singleton strategy instance for *build_system*."""
    inst = _INSTANCES.get(build_system)
    if inst is None:
        raise ValueError(f"Unknown build system: {build_system!r}")
    return inst


def get_all_strategies() -> dict[str, BuildStrategy]:
    """Return the full ``{name: instance}`` mapping."""
    return dict(_INSTANCES)

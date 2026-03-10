"""
Path template resolution service.

All path strings in the editor (``build_dir``, ``install_dir``,
``prefix_path``) are treated as Python :meth:`str.format_map` templates.
This module provides:

* A **variable registry** — the single authoritative list of supported
  placeholder names and their human-readable descriptions.
* :class:`PathContext` — an immutable, dict-backed value object that maps
  registered variable names to their resolved values for one specific node.
* :func:`make_path_context` — constructs a ``PathContext`` from a node
  object and optional overrides.
* :func:`validate_template` — inspects a template string and reports
  any placeholder names that are *not* in the registry.
* :func:`resolve_path` — applies a ``PathContext`` to a template string.

**Extending the variable set** (Open/Closed Principle):
    1. Call ``register_variable("my_var", "Human-readable description")``.
    2. Add ``"my_var": <value>`` to the ``kwargs`` inside
       :func:`make_path_context`.
    3. Done — all call-sites that use :func:`resolve_path` automatically
       gain support for ``{my_var}`` in templates.
"""

from __future__ import annotations

import os
import re
import shutil
import string

# ---------------------------------------------------------------------------
# Variable registry
# ---------------------------------------------------------------------------

VARIABLE_REGISTRY: dict[str, str] = {}


def register_variable(name: str, description: str) -> None:
    """Register *name* as a supported template variable.

    Parameters
    ----------
    name:
        The bare identifier used inside ``{…}`` braces.
    description:
        Human-readable explanation shown in the UI hint label.
    """
    VARIABLE_REGISTRY[name] = description


# Built-in registrations
register_variable("build_type", "CMake build type (Debug, Release, …)")
register_variable("project_name", "Sanitized node title, safe for filesystem paths")
register_variable("vcpkg_path", "vcpkg installation root (auto-detected from VCPKG_ROOT or PATH)")


# ---------------------------------------------------------------------------
# vcpkg detection
# ---------------------------------------------------------------------------

def _detect_vcpkg() -> str:
    """Return the vcpkg root directory, or empty string if not found.

    Detection order:
    1. ``VCPKG_ROOT`` environment variable.
    2. ``vcpkg`` executable on ``PATH`` — parent directory is the root.
    3. Typical convention locations (``C:/vcpkg``, ``D:/vcpkg``,
       ``~/vcpkg``).
    """
    # 1. Explicit env var
    env = os.environ.get("VCPKG_ROOT", "").strip()
    if env and os.path.isdir(env):
        return env.replace("\\", "/")

    # 2. vcpkg on PATH
    exe = shutil.which("vcpkg")
    if exe:
        root = os.path.dirname(os.path.abspath(exe))
        if os.path.isdir(root):
            return root.replace("\\", "/")

    # 3. Common fixed locations
    candidates = [
        "C:/vcpkg",
        "D:/vcpkg",
        os.path.expanduser("~/vcpkg"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path.replace("\\", "/")

    return ""


# Resolved once at import time; empty string when vcpkg is not installed.
VCPKG_ROOT: str = _detect_vcpkg()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    """Strip characters that are unsafe in filesystem path segments."""
    return re.sub(r"[^\w\-.]", "_", name)


# ---------------------------------------------------------------------------
# PathContext
# ---------------------------------------------------------------------------

class PathContext:
    """Immutable mapping of variable names to their resolved string values.

    Backed by an ordinary ``dict`` so it can be passed directly to
    :meth:`str.format_map`.
    """

    __slots__ = ("_vars",)

    def __init__(self, **kwargs: str) -> None:
        self._vars: dict[str, str] = dict(kwargs)

    def as_dict(self) -> dict[str, str]:
        """Return a shallow copy of the internal variable map."""
        return dict(self._vars)

    def __repr__(self) -> str:
        pairs = ", ".join(f"{k}={v!r}" for k, v in self._vars.items())
        return f"PathContext({pairs})"


# ---------------------------------------------------------------------------
# Context factory
# ---------------------------------------------------------------------------

def make_path_context(
    node_obj,
    build_type_override: str | None = None,
) -> PathContext:
    """Build a :class:`PathContext` for *node_obj*.

    Parameters
    ----------
    node_obj:
        Any object that exposes ``buildSettings()`` and ``title()``
        (both :class:`NodeItem` and :class:`NodeProxy` qualify).
    build_type_override:
        When set, takes precedence over the node's own ``build_type``
        field (e.g. when a global build-type is selected in the UI).
    """
    bs = node_obj.buildSettings()
    build_type = build_type_override or bs.build_type
    project_name = _sanitize_name(node_obj.title())

    return PathContext(
        build_type=build_type,
        project_name=project_name,
        vcpkg_path=VCPKG_ROOT,
    )


# ---------------------------------------------------------------------------
# Template validation
# ---------------------------------------------------------------------------

def validate_template(template: str, ctx: PathContext) -> list[str]:
    """Return the list of placeholder names in *template* that are unknown.

    Uses :mod:`string.Formatter` to parse the template so that format
    strings with conversion flags (``{foo!r}``) or format specs
    (``{bar:.2f}``) are handled correctly.

    An empty return list means the template is fully resolvable with *ctx*.
    """
    known = set(ctx.as_dict())
    unknown: list[str] = []
    formatter = string.Formatter()
    try:
        for _, field_name, _, _ in formatter.parse(template):
            if field_name is None:
                continue
            # field_name may be "foo.bar" or "foo[0]" — take the base name
            base = field_name.split(".")[0].split("[")[0]
            if base and base not in known and base not in unknown:
                unknown.append(base)
    except (ValueError, KeyError):
        pass
    return unknown


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_path(template: str, ctx: PathContext) -> str:
    """Substitute all ``{variable}`` placeholders in *template*.

    Assumes the caller has already validated the template with
    :func:`validate_template`.  An unknown placeholder will raise
    :class:`KeyError`; callers that want a graceful fallback should
    call ``validate_template`` first.

    Parameters
    ----------
    template:
        A path string potentially containing ``{build_type}``,
        ``{project_name}``, or any other registered variable.
    ctx:
        The resolved variable values for the current node.
    """
    return template.format_map(ctx.as_dict())

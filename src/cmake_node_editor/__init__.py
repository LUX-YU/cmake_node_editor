"""CMake Conductor package initialization."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cmake_node_editor")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = ["main"]


def main():
    """Convenience re-export — lazy import to avoid loading PyQt6 at import time."""
    from .main import main as _main
    _main()

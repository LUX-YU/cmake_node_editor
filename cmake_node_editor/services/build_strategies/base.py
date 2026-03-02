"""
Abstract base class for build strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...models.data_classes import CommandData


class BuildStrategy(ABC):
    """Interface for generating build commands for a single node."""

    @abstractmethod
    def validate(self, node, project_dir: str) -> str | None:
        """Return an error message if the node is misconfigured, else *None*."""

    @abstractmethod
    def generate_commands(
        self,
        node,
        stage: str,
        build_dir: str,
        install_dir: str,
        prefix_path: str,
    ) -> list[CommandData]:
        """Return :class:`CommandData` entries for the requested *stage*.

        Parameters
        ----------
        node : NodeItem | NodeProxy
            Duck-typed node object.
        stage : str
            ``"configure"``, ``"build"``, ``"install"`` or ``"all"``.
        build_dir : str
            Resolved per-node build directory.
        install_dir : str
            Resolved install directory.
        prefix_path : str
            Resolved ``CMAKE_PREFIX_PATH`` (may be empty for non-CMake).
        """

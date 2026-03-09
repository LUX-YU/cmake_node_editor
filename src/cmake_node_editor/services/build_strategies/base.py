"""
Abstract base class for build strategies.

Each concrete strategy subclass is **the single source of truth** for
everything related to its build system:
- metadata (name, label)
- project-directory validation (creation-time)
- build-time validation and command generation
- which ``BuildSettings`` fields are relevant
- inheritable attributes and how to copy them
- the properties-form widget used in dialogs

Adding a new build system means implementing this ABC and registering
it in :mod:`services.build_strategies.__init__` — **no other files need
modification** (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ...models.data_classes import CommandData

if TYPE_CHECKING:
    from ...views.graphics_items import NodeItem


class BuildStrategy(ABC):
    """Interface for a build system supported by the node editor."""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique machine key, e.g. ``"cmake"``."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable label, e.g. ``"CMake"``."""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @abstractmethod
    def validate(self, node: Any, project_dir: str) -> str | None:
        """Build-time validation. Return an error message or *None*."""

    def validate_project_dir(self, project_dir: str) -> str | None:
        """Creation-time validation of just the project directory.

        The default implementation accepts any existing directory.
        Override to check for strategy-specific marker files
        (e.g. ``CMakeLists.txt``).
        """
        return None

    # ------------------------------------------------------------------
    # Command generation
    # ------------------------------------------------------------------

    @abstractmethod
    def generate_commands(
        self,
        node: Any,
        stage: str,
        build_dir: str,
        install_dir: str,
        prefix_path: str,
        build_type: str = "",
    ) -> list[CommandData]:
        """Return :class:`CommandData` entries for the requested *stage*."""

    # ------------------------------------------------------------------
    # BuildSettings metadata
    # ------------------------------------------------------------------

    def relevant_build_setting_keys(self) -> list[str]:
        """Which :class:`BuildSettings` field names this strategy uses.

        Controls which fields are shown in the properties form and
        which inheritance checkboxes appear in the creation dialog.
        The default returns only the three universal fields.
        """
        return ["build_dir", "install_dir"]

    # ------------------------------------------------------------------
    # Inheritance / copy support
    # ------------------------------------------------------------------

    def copyable_node_attrs(self) -> list[tuple[str, str]]:
        """Return ``(key, label)`` pairs for strategy-specific inheritable
        attributes shown in the creation dialog's "Copy Attributes" group.

        Default returns nothing.
        """
        return []

    def copy_node_data(
        self,
        target_node: "NodeItem",
        source_node: "NodeItem",
        selected_keys: set[str],
    ) -> None:
        """Copy strategy-specific data from *source_node* to *target_node*.

        Called by the creation dialog when the user inherits from an
        existing node.  *selected_keys* is the set of keys the user
        checked.  Default is a no-op.
        """

    # ------------------------------------------------------------------
    # Properties form factory
    # ------------------------------------------------------------------

    @abstractmethod
    def create_properties_form(self) -> Any:
        """Return a **new** QWidget instance for editing strategy-specific
        node settings in the Properties / Batch-Edit dialogs.

        The returned widget **must** implement two methods::

            load_from_node(node: NodeItem) -> None
            apply_to_node(node: NodeItem) -> None

        Using a lazy import inside this method avoids circular dependencies
        between the ``services`` and ``dialogs`` layers.
        """

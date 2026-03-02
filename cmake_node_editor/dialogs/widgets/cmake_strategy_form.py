"""
Strategy-specific properties form for **CMake** nodes.

Wraps :class:`CMakeOptionsEditor` and the CMake-specific subset of
:class:`BuildSettingsForm`.  Implements the ``load_from_node`` /
``apply_to_node`` protocol expected by :class:`NodePropertiesDialog`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from .cmake_options_editor import CMakeOptionsEditor
from .build_settings_form import BuildSettingsForm

if TYPE_CHECKING:
    from ...views.graphics_items import NodeItem


class CMakeStrategyForm(QWidget):
    """Composite form: CMake options + full build settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.cmake_options_editor = CMakeOptionsEditor()
        layout.addWidget(self.cmake_options_editor)

        self.build_settings_form = BuildSettingsForm()
        layout.addWidget(self.build_settings_form)

    # ------------------------------------------------------------------
    # Protocol: load_from_node / apply_to_node
    # ------------------------------------------------------------------

    def load_from_node(self, node: "NodeItem") -> None:
        self.cmake_options_editor.set_options(node.cmakeOptions())
        self.build_settings_form.load_from_settings(node.buildSettings())

    def apply_to_node(self, node: "NodeItem") -> None:
        node.setCMakeOptions(self.cmake_options_editor.get_options())
        node.setBuildSettings(self.build_settings_form.to_settings())

    # ------------------------------------------------------------------
    # Optional validation hook (called by Properties dialog on OK)
    # ------------------------------------------------------------------

    def validate(self) -> str | None:
        """Return an error message string or *None*."""
        return self.cmake_options_editor.validate()

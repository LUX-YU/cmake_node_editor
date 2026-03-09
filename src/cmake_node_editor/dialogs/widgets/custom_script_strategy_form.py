"""
Strategy-specific properties form for **Custom Script** nodes.

Wraps :class:`CustomCommandsForm` and a minimal :class:`BuildSettingsForm`
showing only the generic fields (build_dir, install_dir).
Implements the ``load_from_node`` / ``apply_to_node`` protocol expected by
:class:`NodePropertiesDialog`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit

from ...models.data_classes import BuildSettings
from ...constants import DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE
from .custom_commands_form import CustomCommandsForm

if TYPE_CHECKING:
    from ...views.graphics_items import NodeItem


class CustomScriptStrategyForm(QWidget):
    """Composite form: generic build paths + custom commands."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._original_build_type = DEFAULT_BUILD_TYPE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Generic build-path fields
        path_form = QFormLayout()
        self.edit_build_dir = QLineEdit(DEFAULT_BUILD_DIR)
        path_form.addRow("Build Directory:", self.edit_build_dir)

        self.edit_install_dir = QLineEdit(DEFAULT_INSTALL_DIR)
        path_form.addRow("Install Directory:", self.edit_install_dir)

        layout.addLayout(path_form)

        # Custom commands
        self.custom_commands_form = CustomCommandsForm()
        layout.addWidget(self.custom_commands_form)

    # ------------------------------------------------------------------
    # Protocol: load_from_node / apply_to_node
    # ------------------------------------------------------------------

    def load_from_node(self, node: "NodeItem") -> None:
        bs = node.buildSettings()
        self._original_build_type = bs.build_type
        self.edit_build_dir.setText(bs.build_dir)
        self.edit_install_dir.setText(bs.install_dir)
        self.custom_commands_form.load_from(node.customCommands())

    def apply_to_node(self, node: "NodeItem") -> None:
        # Preserve existing build settings, only overwrite the generic fields
        bs = node.buildSettings()
        updated_bs = BuildSettings(
            build_dir=self.edit_build_dir.text().strip(),
            install_dir=self.edit_install_dir.text().strip(),
            build_type=self._original_build_type,
            prefix_path=bs.prefix_path,
            toolchain_file=bs.toolchain_file,
            generator=bs.generator,
            c_compiler=bs.c_compiler,
            cxx_compiler=bs.cxx_compiler,
        )
        node.setBuildSettings(updated_bs)
        node.setCustomCommands(self.custom_commands_form.to_commands())

    # ------------------------------------------------------------------
    # Validation hook
    # ------------------------------------------------------------------

    def validate(self) -> str | None:
        """Custom Script forms have no special validation."""
        return None

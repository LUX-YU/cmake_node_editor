"""
Reusable widget for editing :class:`CustomCommands`.

Provides three script editors (configure / build / install) for
non-CMake build systems.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPlainTextEdit,
)

from ...models.data_classes import CustomCommands


class CustomCommandsForm(QWidget):
    """Embeddable form for editing :class:`CustomCommands`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Configure Script (shell commands):"))
        self.edit_configure = QPlainTextEdit()
        self.edit_configure.setPlaceholderText(
            "e.g.  cd {project_dir} && ./bootstrap.sh"
        )
        self.edit_configure.setMinimumHeight(80)
        layout.addWidget(self.edit_configure)

        layout.addWidget(QLabel("Build Script (shell commands):"))
        self.edit_build = QPlainTextEdit()
        self.edit_build.setPlaceholderText(
            "e.g.  cd {project_dir} && make -j$(nproc)"
        )
        self.edit_build.setMinimumHeight(80)
        layout.addWidget(self.edit_build)

        layout.addWidget(QLabel("Install Script (shell commands):"))
        self.edit_install = QPlainTextEdit()
        self.edit_install.setPlaceholderText(
            "e.g.  cd {project_dir} && make install PREFIX={install_dir}"
        )
        self.edit_install.setMinimumHeight(80)
        layout.addWidget(self.edit_install)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_from(self, cc: CustomCommands | None) -> None:
        """Populate the form from a ``CustomCommands`` instance."""
        if cc is None:
            cc = CustomCommands()
        self.edit_configure.setPlainText(cc.configure_script)
        self.edit_build.setPlainText(cc.build_script)
        self.edit_install.setPlainText(cc.install_script)

    def to_commands(self) -> CustomCommands:
        """Create a ``CustomCommands`` from the current form values."""
        return CustomCommands(
            configure_script=self.edit_configure.toPlainText(),
            build_script=self.edit_build.toPlainText(),
            install_script=self.edit_install.toPlainText(),
        )

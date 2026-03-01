"""
Reusable widget for editing :class:`BuildSettings`.

Provides input fields for every attribute of ``BuildSettings`` and
convenience methods to load from / export to a ``BuildSettings`` instance.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QPlainTextEdit, QLabel,
)

from ...models.data_classes import BuildSettings
from ...constants import (
    DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, BUILD_TYPES, GENERATORS,
)


class BuildSettingsForm(QWidget):
    """Embeddable form for editing :class:`BuildSettings`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)

        self.edit_build_dir = QLineEdit(DEFAULT_BUILD_DIR)
        form.addRow("Build Directory:", self.edit_build_dir)

        self.combo_build_type = QComboBox()
        self.combo_build_type.addItems(BUILD_TYPES)
        form.addRow("Build Type:", self.combo_build_type)

        self.edit_install_dir = QLineEdit(DEFAULT_INSTALL_DIR)
        form.addRow("Install Directory:", self.edit_install_dir)

        self.edit_prefix_path = QLineEdit(DEFAULT_INSTALL_DIR)
        form.addRow("PREFIX_PATH:", self.edit_prefix_path)

        self.edit_toolchain = QLineEdit()
        form.addRow("Toolchain File:", self.edit_toolchain)

        self.combo_generator = QComboBox()
        self.combo_generator.addItems(GENERATORS)
        form.addRow("CMake Generator:", self.combo_generator)

        self.edit_c_compiler = QLineEdit()
        form.addRow("C Compiler:", self.edit_c_compiler)

        self.edit_cxx_compiler = QLineEdit()
        form.addRow("C++ Compiler:", self.edit_cxx_compiler)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_from_settings(self, bs: BuildSettings) -> None:
        """Populate the form from a ``BuildSettings`` instance."""
        self.edit_build_dir.setText(bs.build_dir)

        idx_bt = self.combo_build_type.findText(bs.build_type)
        if idx_bt >= 0:
            self.combo_build_type.setCurrentIndex(idx_bt)
        else:
            self.combo_build_type.setCurrentText(bs.build_type)

        self.edit_install_dir.setText(bs.install_dir)
        self.edit_prefix_path.setText(bs.prefix_path)
        self.edit_toolchain.setText(bs.toolchain_file)

        if bs.generator:
            gen_idx = self.combo_generator.findText(bs.generator)
            if gen_idx >= 0:
                self.combo_generator.setCurrentIndex(gen_idx)
            else:
                self.combo_generator.setCurrentText(bs.generator)
        else:
            self.combo_generator.setCurrentIndex(0)

        self.edit_c_compiler.setText(bs.c_compiler)
        self.edit_cxx_compiler.setText(bs.cxx_compiler)

    def to_settings(self) -> BuildSettings:
        """Create a ``BuildSettings`` from the current form values."""
        generator = (
            ""
            if self.combo_generator.currentIndex() == 0
            else self.combo_generator.currentText()
        )
        return BuildSettings(
            build_dir=self.edit_build_dir.text().strip(),
            install_dir=self.edit_install_dir.text().strip(),
            build_type=self.combo_build_type.currentText(),
            prefix_path=self.edit_prefix_path.text().strip(),
            toolchain_file=self.edit_toolchain.text().strip(),
            generator=generator,
            c_compiler=self.edit_c_compiler.text().strip(),
            cxx_compiler=self.edit_cxx_compiler.text().strip(),
        )

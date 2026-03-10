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
    DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE, GENERATORS,
)
from ...services.path_resolver import VARIABLE_REGISTRY, validate_template, PathContext

_HINT_STYLE_OK = ""
_HINT_STYLE_ERR = "border: 1px solid red;"


class BuildSettingsForm(QWidget):
    """Embeddable form for editing :class:`BuildSettings`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._original_build_type = DEFAULT_BUILD_TYPE

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)

        # Available-variable hint (derived from registry, always in sync)
        vars_hint = ", ".join(f"{{{k}}}" for k in VARIABLE_REGISTRY)
        hint_label = QLabel(f"Available variables: {vars_hint}")
        hint_label.setStyleSheet("color: gray; font-size: 10px;")
        hint_label.setWordWrap(True)
        form.addRow("", hint_label)

        self.edit_build_dir = QLineEdit(DEFAULT_BUILD_DIR)
        form.addRow("Build Directory:", self.edit_build_dir)

        self.edit_install_dir = QLineEdit(DEFAULT_INSTALL_DIR)
        form.addRow("Install Directory:", self.edit_install_dir)

        self.edit_prefix_path = QLineEdit(DEFAULT_INSTALL_DIR)
        form.addRow("Prefix Path:", self.edit_prefix_path)

        self.edit_toolchain = QLineEdit()
        form.addRow("Toolchain File:", self.edit_toolchain)

        self.combo_generator = QComboBox()
        self.combo_generator.addItems(GENERATORS)
        form.addRow("CMake Generator:", self.combo_generator)

        self.edit_c_compiler = QLineEdit()
        form.addRow("C Compiler:", self.edit_c_compiler)

        self.edit_cxx_compiler = QLineEdit()
        form.addRow("C++ Compiler:", self.edit_cxx_compiler)

        # Wire validation to path fields
        _dummy_ctx = PathContext(**{k: "x" for k in VARIABLE_REGISTRY})
        for field in (self.edit_build_dir, self.edit_install_dir, self.edit_prefix_path):
            field.textChanged.connect(
                lambda text, f=field, c=_dummy_ctx: self._validatePathField(f, c)
            )

    @staticmethod
    def _validatePathField(field: QLineEdit, ctx: PathContext) -> None:
        unknown = validate_template(field.text(), ctx)
        field.setStyleSheet(_HINT_STYLE_ERR if unknown else _HINT_STYLE_OK)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_from_settings(self, bs: BuildSettings) -> None:
        """Populate the form from a ``BuildSettings`` instance."""
        self._original_build_type = bs.build_type
        self.edit_build_dir.setText(bs.build_dir)
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
            build_type=self._original_build_type,
            prefix_path=self.edit_prefix_path.text().strip(),
            toolchain_file=self.edit_toolchain.text().strip(),
            generator=generator,
            c_compiler=self.edit_c_compiler.text().strip(),
            cxx_compiler=self.edit_cxx_compiler.text().strip(),
        )

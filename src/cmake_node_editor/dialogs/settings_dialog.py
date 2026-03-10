"""Application settings dialog (style, grid opacity, link color, theme)."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QLabel, QStyleFactory, QPushButton, QColorDialog,
    QHBoxLayout, QFileDialog,
)

_CUSTOM_LABEL = "Custom QSS file..."


class SettingsDialog(QDialog):
    """Dialog for general application settings."""

    def __init__(self, current_style: str, current_opacity: float,
                 current_link_color: QColor, current_theme_name: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(340)

        # ── Theme selector ────────────────────────────────────────────
        from ..theme import ThemeRegistry
        self._custom_qss_path: str = ""
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(ThemeRegistry.names())
        self.theme_combo.addItem(_CUSTOM_LABEL)
        # pre-select current theme (or "Custom QSS..." if external was used)
        idx = self.theme_combo.findText(current_theme_name,
                                         Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._onThemeChanged)

        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.clicked.connect(self._browseQss)
        self._browse_btn.setVisible(
            self.theme_combo.currentText() == _CUSTOM_LABEL
        )

        theme_row = QHBoxLayout()
        theme_row.addWidget(self.theme_combo, stretch=1)
        theme_row.addWidget(self._browse_btn)

        # ── Application style ─────────────────────────────────────────
        self.style_combo = QComboBox()
        self.style_combo.addItems(QStyleFactory.keys())
        idx = self.style_combo.findText(current_style, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)

        # ── Grid opacity ──────────────────────────────────────────────
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.0, 1.0)
        self.opacity_spin.setSingleStep(0.05)
        self.opacity_spin.setValue(current_opacity)

        # ── Link color ────────────────────────────────────────────────
        self.link_color = QColor(current_link_color)
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self._chooseColor)
        self._updateColorBtn()

        # ── Layout ────────────────────────────────────────────────────
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow(QLabel("Theme:"), theme_row)
        form.addRow(QLabel("Application Style:"), self.style_combo)
        form.addRow(QLabel("Grid Opacity:"), self.opacity_spin)
        form.addRow(QLabel("Link Color:"), self.color_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _onThemeChanged(self):
        is_custom = self.theme_combo.currentText() == _CUSTOM_LABEL
        self._browse_btn.setVisible(is_custom)
        if not is_custom:
            self._custom_qss_path = ""

    def _browseQss(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select QSS Stylesheet", "", "Qt Stylesheets (*.qss);;All files (*)"
        )
        if path:
            self._custom_qss_path = path

    def getValues(self) -> tuple:
        """Return ``(style_name, opacity, link_color, theme_name, custom_qss_path)``.

        *theme_name* is empty when a custom QSS file is used.
        *custom_qss_path* is empty when a built-in theme is selected.
        """
        theme_text = self.theme_combo.currentText()
        if theme_text == _CUSTOM_LABEL:
            theme_name = ""
            custom_path = self._custom_qss_path
        else:
            theme_name = theme_text
            custom_path = ""
        return (
            self.style_combo.currentText(),
            self.opacity_spin.value(),
            self.link_color,
            theme_name,
            custom_path,
        )

    def _chooseColor(self):
        col = QColorDialog.getColor(self.link_color, self, "Select Link Color")
        if col.isValid():
            self.link_color = col
            self._updateColorBtn()

    def _updateColorBtn(self):
        self.color_btn.setStyleSheet(f"background-color: {self.link_color.name()};")

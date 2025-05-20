from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QLabel, QStyleFactory, QPushButton, QColorDialog
)

class SettingsDialog(QDialog):
    """Dialog for general application settings."""

    def __init__(self, current_style: str, current_opacity: float, current_link_color: QColor, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.style_combo = QComboBox()
        self.style_combo.addItems(QStyleFactory.keys())
        idx = self.style_combo.findText(current_style, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)

        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.0, 1.0)
        self.opacity_spin.setSingleStep(0.05)
        self.opacity_spin.setValue(current_opacity)

        self.link_color = QColor(current_link_color)
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self.chooseColor)
        self.updateColorBtn()

        form = QFormLayout(self)
        form.addRow(QLabel("Application Style:"), self.style_combo)
        form.addRow(QLabel("Grid Opacity:"), self.opacity_spin)
        form.addRow(QLabel("Link Color:"), self.color_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

    def getValues(self):
        """Return the chosen style, grid opacity and link color."""
        return self.style_combo.currentText(), self.opacity_spin.value(), self.link_color

    def chooseColor(self):
        col = QColorDialog.getColor(self.link_color, self, "Select Link Color")
        if col.isValid():
            self.link_color = col
            self.updateColorBtn()

    def updateColorBtn(self):
        self.color_btn.setStyleSheet(f"background-color: {self.link_color.name()};")

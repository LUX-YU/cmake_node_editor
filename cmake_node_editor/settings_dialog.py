from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QLabel, QStyleFactory
)

class SettingsDialog(QDialog):
    """Dialog for general application settings."""

    def __init__(self, current_style: str, current_opacity: float, parent=None):
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

        form = QFormLayout(self)
        form.addRow(QLabel("Application Style:"), self.style_combo)
        form.addRow(QLabel("Grid Opacity:"), self.opacity_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)

    def getValues(self):
        """Return the chosen style name and grid opacity."""
        return self.style_combo.currentText(), self.opacity_spin.value()

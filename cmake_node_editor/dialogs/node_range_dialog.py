"""Small dialog for selecting a start/end node-ID range."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDialogButtonBox, QMessageBox,
)


class NodeRangeDialog(QDialog):
    """Dialog to input a start and end node ID."""

    def __init__(self, min_id: int, max_id: int, parent=None, valid_ids: set[int] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Select Node ID Range")
        self._valid_ids = valid_ids
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.start_spin = QSpinBox()
        self.start_spin.setRange(min_id, max_id)
        self.start_spin.setValue(min_id)
        self.end_spin = QSpinBox()
        self.end_spin.setRange(min_id, max_id)
        self.end_spin.setValue(max_id)
        form.addRow("Start ID:", self.start_spin)
        form.addRow("End ID:", self.end_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        s, e = self.start_spin.value(), self.end_spin.value()
        if self._valid_ids is not None:
            missing = []
            if s not in self._valid_ids:
                missing.append(f"Start ID {s}")
            if e not in self._valid_ids:
                missing.append(f"End ID {e}")
            if missing:
                QMessageBox.warning(self, "Invalid ID", f"{', '.join(missing)} does not exist.")
                return
        if e < s:
            QMessageBox.warning(self, "Invalid Range", "End ID must be >= Start ID.")
            return
        self.accept()

    def getValues(self) -> tuple[int, int]:
        return self.start_spin.value(), self.end_spin.value()

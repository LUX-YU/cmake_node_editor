"""
Reusable widget for editing CMake ``-D`` options as a dynamic list of rows.

Each row contains a ``QLineEdit`` and a *Delete* button. The editor exposes
simple ``get_options`` / ``set_options`` helpers so that host dialogs do not
need to manage individual row widgets.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QScrollArea,
)


class CMakeOptionsEditor(QWidget):
    """Dynamic list of CMake option rows (``-Dkey=value`` strings)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[QWidget, QLineEdit]] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Internal container so QScrollArea can wrap it
        self._options_layout = QVBoxLayout()

        # "Add" button
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("Add CMake Option")
        self._btn_add.clicked.connect(lambda: self.add_option())
        btn_row.addWidget(self._btn_add)
        self._options_layout.addLayout(btn_row)

        container = QWidget()
        container.setLayout(self._options_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setMinimumHeight(150)
        self._layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_option(self, text: str = "") -> None:
        """Append a new option row with *text* pre-filled."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(text)
        btn_delete = QPushButton("Delete")
        row_layout.addWidget(line_edit)
        row_layout.addWidget(btn_delete)

        btn_delete.clicked.connect(lambda: self._remove_row(row_widget))

        self._rows.append((row_widget, line_edit))
        # Insert before the "Add" button row
        self._options_layout.insertWidget(self._options_layout.count() - 1, row_widget)

    def get_options(self) -> list[str]:
        """Return the current list of non-empty, validated option strings."""
        result: list[str] = []
        for _, line_edit in self._rows:
            val = line_edit.text().strip()
            if val:
                result.append(val)
        return result

    def validate(self) -> str | None:
        """Return an error message if any option is malformed, else *None*."""
        import re
        pattern = re.compile(r'^-D[A-Za-z_][A-Za-z0-9_]*(:[A-Z]+)?=.+$')
        for i, (_, line_edit) in enumerate(self._rows):
            val = line_edit.text().strip()
            if val and not pattern.match(val):
                return (
                    f"Option row {i+1} is malformed: '{val}'.\n"
                    f"Expected format: -DKEY=VALUE or -DKEY:TYPE=VALUE"
                )
        return None

    def set_options(self, options: list[str]) -> None:
        """Clear current rows and populate from *options*."""
        self.clear()
        for opt in options:
            self.add_option(opt)

    def clear(self) -> None:
        """Remove all option rows."""
        for row_widget, _ in self._rows:
            self._options_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        self._rows.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _remove_row(self, row_widget: QWidget) -> None:
        for i, (rw, _le) in enumerate(self._rows):
            if rw is row_widget:
                self._options_layout.removeWidget(rw)
                rw.deleteLater()
                self._rows.pop(i)
                break

"""
Path Variables Dialog — shows every registered template variable
together with its resolved value for the currently selected node.

If no node is selected, only the variable name and description are shown.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QWidget, QFrame, QPushButton,
    QGridLayout,
)

from ..services.path_resolver import VARIABLE_REGISTRY, make_path_context

# ---------------------------------------------------------------------------
# Re-use the same design tokens as NodePropertiesDialog
# ---------------------------------------------------------------------------
_BG       = "#1e1e2e"
_BG_PANEL = "#2a2a3e"
_BG_INPUT = "#313145"
_BORDER   = "#44445a"
_ACCENT   = "#7c9ef8"
_ACCENT2  = "#56d4c8"
_TEXT     = "#cdd6f4"
_TEXT_DIM = "#6c7086"
_TEXT_ERR = "#f38ba8"
_RADIUS   = "6px"

_QSS = f"""
QDialog {{
    background: {_BG};
    color: {_TEXT};
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: {_BG_PANEL}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER}; border-radius: 4px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel {{ color: {_TEXT}; background: transparent; }}
QPushButton {{
    background: {_BG_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: {_RADIUS};
    padding: 6px 22px;
    font-weight: 500;
    min-width: 80px;
}}
QPushButton:hover {{
    background: #35355a;
    border-color: {_ACCENT};
}}
QPushButton:pressed {{
    background: #28283e;
}}
"""

_MONO = "font-family:'Consolas','Courier New',monospace;font-size:12px;background:transparent;"


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color:{_BORDER};background:{_BORDER};border:none;max-height:1px;")
    return line


class PathVariablesDialog(QDialog):
    """Non-modal-friendly dialog listing all path template variables."""

    def __init__(self, node_item=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Path Variables")
        self.resize(600, 420)
        self.setMinimumWidth(480)
        self.setStyleSheet(_QSS)

        self._node = node_item
        self._buildUI()

    # ------------------------------------------------------------------
    def _buildUI(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Title bar ─────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2b2d4a,stop:1 {_BG});"
            f"border-bottom:1px solid {_BORDER};"
        )
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(16, 0, 16, 0)
        lbl_title = QLabel("Path Variables")
        lbl_title.setStyleSheet(
            f"color:{_TEXT};font-size:14px;font-weight:bold;background:transparent;border:none;"
        )
        tb.addWidget(lbl_title)
        tb.addStretch()

        if self._node is not None:
            ctx_badge = QLabel(f"context: {self._node.title()}")
            ctx_badge.setStyleSheet(
                f"color:{_ACCENT};font-size:12px;background:transparent;border:none;"
            )
            tb.addWidget(ctx_badge)
        else:
            no_ctx = QLabel("no node selected — values not resolved")
            no_ctx.setStyleSheet(
                f"color:{_TEXT_DIM};font-size:12px;background:transparent;border:none;"
            )
            tb.addWidget(no_ctx)

        root.addWidget(title_bar)

        # ── Scrollable grid ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        inner.setStyleSheet(f"background:{_BG};")
        grid = QGridLayout(inner)
        grid.setContentsMargins(16, 16, 16, 8)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(0)
        grid.setColumnStretch(2, 1)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # column headers
        def _hdr(txt):
            l = QLabel(txt)
            l.setStyleSheet(
                f"color:{_TEXT_DIM};font-size:11px;font-weight:bold;"
                f"letter-spacing:1px;background:transparent;"
            )
            return l

        grid.addWidget(_hdr("VARIABLE"), 0, 0)
        grid.addWidget(_hdr("DESCRIPTION"), 0, 1)
        grid.addWidget(_hdr("RESOLVED VALUE"), 0, 2)
        grid.addWidget(_divider(), 1, 0, 1, 3)

        # resolve values if we have a node
        resolved: dict[str, str] = {}
        if self._node is not None:
            ctx = make_path_context(self._node)
            resolved = ctx.as_dict()

        row = 2
        for var_name, description in VARIABLE_REGISTRY.items():
            # variable name
            lbl_var = QLabel(f"{{{var_name}}}")
            lbl_var.setStyleSheet(f"color:{_ACCENT2};{_MONO}padding:8px 0;")
            lbl_var.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lbl_var, row, 0)

            # description
            lbl_desc = QLabel(description)
            lbl_desc.setStyleSheet(f"color:{_TEXT_DIM};font-size:12px;background:transparent;padding:8px 0;")
            lbl_desc.setWordWrap(True)
            grid.addWidget(lbl_desc, row, 1)

            # resolved value
            if self._node is not None:
                val = resolved.get(var_name, "")
                if val:
                    lbl_val = QLabel(val)
                    lbl_val.setStyleSheet(f"color:{_TEXT};{_MONO}padding:8px 0;")
                else:
                    lbl_val = QLabel("(not found)")
                    lbl_val.setStyleSheet(f"color:{_TEXT_ERR};{_MONO}padding:8px 0;")
            else:
                lbl_val = QLabel("—")
                lbl_val.setStyleSheet(f"color:{_TEXT_DIM};{_MONO}padding:8px 0;")

            lbl_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl_val.setWordWrap(True)
            grid.addWidget(lbl_val, row, 2)

            row += 1
            grid.addWidget(_divider(), row, 0, 1, 3)
            row += 1

        grid.setRowStretch(row, 1)

        # ── Footer ────────────────────────────────────────────────────
        footer = QWidget()
        footer.setStyleSheet(f"background:{_BG_PANEL};border-top:1px solid {_BORDER};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        fl.addWidget(btn_close)
        root.addWidget(footer)

"""
Dependency Preview Dialog — shows the minimal dependency build order
before executing a "Build To This" action.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QDialogButtonBox,
)

if TYPE_CHECKING:
    from ..views.graphics_items import NodeItem


class DependencyPreviewDialog(QDialog):
    """Display the ordered list of nodes that will be built, and let the
    user confirm or cancel."""

    def __init__(
        self,
        stage: str,
        target_node: "NodeItem",
        ordered_nodes: list["NodeItem"],
        parent=None,
    ):
        super().__init__(parent)
        stage_label = {
            "configure": "Configure",
            "build": "Build",
            "install": "Install",
            "all": "Generate (Full)",
        }.get(stage, stage.capitalize())

        self.setWindowTitle(f"{stage_label} To — Dependency Preview")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>{stage_label}</b> target: <b>{target_node.title()}</b><br>"
            f"The following <b>{len(ordered_nodes)}</b> node(s) will be processed "
            f"in order:"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._list = QListWidget()
        for i, node in enumerate(ordered_nodes, 1):
            item = QListWidgetItem(f"{i}. {node.title()}  (ID {node.id()})")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._list.addItem(item)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

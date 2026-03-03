"""
Batch Edit Dialog — **strategy-driven** layout.

Detects whether all selected nodes share a common build system.
If so, shows the strategy-specific form.  If mixed, only the shared fields
(pre-build / post-install scripts) are editable.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget,
    QLabel, QPushButton, QPlainTextEdit,
    QDialogButtonBox, QListWidget, QListWidgetItem, QMessageBox,
    QSplitter,
)

from ..views.graphics_items import NodeItem
from ..services.build_strategies import get_strategy


class BatchEditDialog(QDialog):
    """Dialog for editing multiple :class:`NodeItem` instances at once."""

    def __init__(self, nodes: list[NodeItem], parent=None):
        super().__init__(parent)
        self.nodes = nodes
        self.setWindowTitle("Batch Edit Nodes")
        self.resize(600, 700)

        # Determine common build system (None if mixed)
        systems = {n.buildSystem() for n in nodes}
        self._common_bs: str | None = systems.pop() if len(systems) == 1 else None
        self._strategy_form: QWidget | None = None

        self._buildUI()
        if nodes:
            self._loadFromNode(nodes[0])

    # ------------------------------------------------------------------
    def _buildUI(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # ---- Node selection list ----
        node_widget = QWidget()
        node_layout = QVBoxLayout(node_widget)
        node_layout.addWidget(QLabel("Select Nodes:"))
        self.list_nodes = QListWidget()
        for n in self.nodes:
            item = QListWidgetItem(f"{n.title()} (ID={n.id()})")
            item.setData(Qt.ItemDataRole.UserRole, n)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_nodes.addItem(item)
        node_layout.addWidget(self.list_nodes)
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self._onSelectAll)
        node_layout.addWidget(btn_sel_all)
        splitter.addWidget(node_widget)
        splitter.setStretchFactor(0, 1)

        # ---- Details ----
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        # Strategy-specific form (or info label if mixed)
        if self._common_bs:
            strategy = get_strategy(self._common_bs)
            details_layout.addWidget(
                QLabel(f"Build System: <b>{strategy.label}</b>")
            )
            self._strategy_form = strategy.create_properties_form()
            details_layout.addWidget(self._strategy_form)
        else:
            details_layout.addWidget(
                QLabel("<i>Nodes have mixed build systems — only shared fields "
                       "are editable.</i>")
            )

        # Shared scripts
        details_layout.addWidget(QLabel("Pre-Build Script (py_code_before_build):"))
        self.edit_py_before = QPlainTextEdit()
        details_layout.addWidget(self.edit_py_before)

        details_layout.addWidget(QLabel("Post-Install Script (py_code_after_install):"))
        self.edit_py_after = QPlainTextEdit()
        details_layout.addWidget(self.edit_py_after)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._onAccept)
        buttons.rejected.connect(self.reject)
        details_layout.addWidget(buttons)

        splitter.addWidget(details_widget)
        splitter.setStretchFactor(1, 3)

    # ------------------------------------------------------------------
    def _onAccept(self):
        if self._strategy_form and hasattr(self._strategy_form, "validate"):
            err = self._strategy_form.validate()
            if err:
                QMessageBox.warning(self, "Validation Error", err)
                return
        self.accept()

    def _onSelectAll(self):
        for i in range(self.list_nodes.count()):
            self.list_nodes.item(i).setCheckState(Qt.CheckState.Checked)

    def _loadFromNode(self, node: NodeItem):
        if self._strategy_form and hasattr(self._strategy_form, "load_from_node"):
            self._strategy_form.load_from_node(node)
        self.edit_py_before.setPlainText(node.codeBeforeBuild())
        self.edit_py_after.setPlainText(node.codeAfterInstall())

    # ------------------------------------------------------------------
    def applyToNodes(self) -> bool:
        selected: list[NodeItem] = []
        for i in range(self.list_nodes.count()):
            item = self.list_nodes.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                nd = item.data(Qt.ItemDataRole.UserRole)
                if nd:
                    selected.append(nd)
        if not selected:
            QMessageBox.warning(self, "Warning", "No nodes selected.")
            return False

        for node in selected:
            if self._strategy_form and hasattr(self._strategy_form, "apply_to_node"):
                self._strategy_form.apply_to_node(node)
            node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
            node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

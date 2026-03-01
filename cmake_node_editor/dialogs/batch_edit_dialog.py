"""
Batch Edit Dialog — uses shared ``BuildSettingsForm`` and ``CMakeOptionsEditor``.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget,
    QLabel, QPushButton, QPlainTextEdit,
    QDialogButtonBox, QListWidget, QListWidgetItem, QMessageBox,
    QSplitter,
)

from ..models.data_classes import BuildSettings
from ..views.graphics_items import NodeItem
from .widgets.build_settings_form import BuildSettingsForm
from .widgets.cmake_options_editor import CMakeOptionsEditor


class BatchEditDialog(QDialog):
    """Dialog for editing multiple :class:`NodeItem` instances at once."""

    def __init__(self, nodes: list[NodeItem], parent=None):
        super().__init__(parent)
        self.nodes = nodes
        self.setWindowTitle("Batch Edit Nodes")
        self.resize(600, 700)

        self._buildUI()
        if nodes:
            self.loadFromNode(nodes[0])

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

        # CMake options (shared widget)
        self.cmake_options_editor = CMakeOptionsEditor()
        details_layout.addWidget(self.cmake_options_editor)

        # Build settings (shared widget)
        self.build_settings_form = BuildSettingsForm()
        details_layout.addWidget(self.build_settings_form)

        # Scripts
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
        opt_err = self.cmake_options_editor.validate()
        if opt_err:
            QMessageBox.warning(self, "Invalid CMake Options", opt_err)
            return
        self.accept()

    # ------------------------------------------------------------------
    def _onSelectAll(self):
        for i in range(self.list_nodes.count()):
            self.list_nodes.item(i).setCheckState(Qt.CheckState.Checked)

    def loadFromNode(self, node: NodeItem):
        self.cmake_options_editor.set_options(node.cmakeOptions())
        self.build_settings_form.load_from_settings(node.buildSettings())
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

        new_opts = self.cmake_options_editor.get_options()
        bs = self.build_settings_form.to_settings()

        for node in selected:
            node.setCMakeOptions(new_opts)
            node.setBuildSettings(bs)
            node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
            node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

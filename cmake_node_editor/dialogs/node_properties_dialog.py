"""
Node Properties Dialog — uses shared ``BuildSettingsForm`` and ``CMakeOptionsEditor``.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit,
    QDialogButtonBox, QMessageBox,
)

from ..models.data_classes import BuildSettings
from ..views.graphics_items import NodeItem
from .widgets.build_settings_form import BuildSettingsForm
from .widgets.cmake_options_editor import CMakeOptionsEditor


class NodePropertiesDialog(QDialog):
    """Modal dialog for editing a single :class:`NodeItem`'s properties."""

    def __init__(self, node_item: NodeItem, parent=None):
        super().__init__(parent)
        self.node_item = node_item
        self.setWindowTitle(f"Edit Node - {node_item.title()}")
        self.resize(700, 800)

        self._buildUI()
        self.loadFromNode(node_item)

    # ------------------------------------------------------------------
    def _buildUI(self):
        layout = QVBoxLayout(self)

        # Project path (first — most important field)
        form_proj = QFormLayout()
        self.edit_node_project_path = QLineEdit()
        form_proj.addRow("Project Path:", self.edit_node_project_path)
        layout.addLayout(form_proj)

        # Name
        form_name = QFormLayout()
        self.edit_node_name = QLineEdit()
        form_name.addRow("Name:", self.edit_node_name)
        layout.addLayout(form_name)

        # CMake options (shared widget)
        self.cmake_options_editor = CMakeOptionsEditor()
        layout.addWidget(self.cmake_options_editor)

        # Build settings (shared widget)
        self.build_settings_form = BuildSettingsForm()
        layout.addWidget(self.build_settings_form)

        # Scripts
        layout.addWidget(QLabel("Pre-Build Script (py_code_before_build):"))
        self.edit_py_before = QPlainTextEdit()
        layout.addWidget(self.edit_py_before)

        layout.addWidget(QLabel("Post-Install Script (py_code_after_install):"))
        self.edit_py_after = QPlainTextEdit()
        layout.addWidget(self.edit_py_after)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._onAccept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _onAccept(self):
        opt_err = self.cmake_options_editor.validate()
        if opt_err:
            QMessageBox.warning(self, "Invalid CMake Options", opt_err)
            return
        self.accept()

    # ------------------------------------------------------------------
    def loadFromNode(self, node: NodeItem):
        self.edit_node_name.setText(node.title())
        self.edit_node_project_path.setText(node.projectPath())

        self.cmake_options_editor.set_options(node.cmakeOptions())
        self.build_settings_form.load_from_settings(node.buildSettings())

        self.edit_py_before.setPlainText(node.codeBeforeBuild())
        self.edit_py_after.setPlainText(node.codeAfterInstall())

    # ------------------------------------------------------------------
    def applyToNode(self) -> bool:
        node = self.node_item

        new_title = self.edit_node_name.text().strip()
        if not new_title:
            new_title = f"Node_{node.id()}"
        elif any(n.title() == new_title and n != node for n in node.scene().nodes):
            QMessageBox.warning(self, "Warning", f"Node name '{new_title}' already exists.")
            return False

        node.updateTitle(new_title)
        node.setCMakeOptions(self.cmake_options_editor.get_options())
        node.setProjectPath(self.edit_node_project_path.text().strip())
        node.setBuildSettings(self.build_settings_form.to_settings())
        node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
        node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

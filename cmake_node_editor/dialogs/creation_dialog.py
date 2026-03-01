"""
Node Creation Dialog — uses shared ``CMakeOptionsEditor``.
"""

import os
from dataclasses import fields

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QWidget, QFileDialog, QMessageBox, QDialogButtonBox,
    QScrollArea, QCheckBox, QComboBox,
)

from ..models.data_classes import NodeData
from .widgets.cmake_options_editor import CMakeOptionsEditor


class NodeCreationDialog(QDialog):
    """
    Dialog that lets the user create a new node with optional inheritance
    from an existing node.
    """

    def __init__(self, parent=None, existing_nodes=None):
        super().__init__(parent)
        self.existing_nodes = existing_nodes if existing_nodes else []
        self.setWindowTitle("Create New Node")
        self.resize(600, 500)

        # Project path (first — auto-fills node name)
        self.project_path_edit = QLineEdit()
        self.project_path_edit.textChanged.connect(self._onProjectPathChanged)
        self.btn_browse_project = QPushButton("Browse Folder")
        self.btn_browse_project.clicked.connect(self._onBrowseProject)

        # Node name
        self.node_name_edit = QLineEdit()
        self._name_manually_set = False
        self.node_name_edit.textEdited.connect(self._onNameEdited)

        # Inheritance
        self.inherit_combo = QComboBox()
        self.inherit_combo.addItem("None")
        for n in self.existing_nodes:
            self.inherit_combo.addItem(n.title())

        # Dynamically create checkboxes for inheritable attributes
        self.attr_checkboxes: list[QCheckBox] = []
        skip_fields = {"node_id", "title", "pos_x", "pos_y"}
        for f in fields(NodeData):
            if f.name in skip_fields:
                continue
            cb = QCheckBox(f.name)
            self.attr_checkboxes.append(cb)

        # CMake options (shared widget)
        self.cmake_options_editor = CMakeOptionsEditor()

        # Build the form — Project Path first
        form = QFormLayout()

        proj_path_layout = QHBoxLayout()
        proj_path_layout.addWidget(self.project_path_edit)
        proj_path_layout.addWidget(self.btn_browse_project)
        form.addRow("Project Path:", proj_path_layout)

        form.addRow("Node Name:", self.node_name_edit)
        form.addRow("Inherit From:", self.inherit_combo)

        inherit_layout = QVBoxLayout()
        for cb in self.attr_checkboxes:
            inherit_layout.addWidget(cb)
        form.addRow("Copy Attributes:", inherit_layout)

        form.addRow("CMake Options:", self.cmake_options_editor)

        # OK / Cancel
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self._onAccept)
        self.buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addWidget(self.buttons)

    # ------------------------------------------------------------------
    def _onProjectPathChanged(self, text: str):
        """Auto-fill node name from the last folder component."""
        if self._name_manually_set:
            return
        text = text.strip().rstrip('/').rstrip('\\')
        if text:
            basename = os.path.basename(text)
            if basename:
                self.node_name_edit.setText(basename)

    def _onNameEdited(self, _text: str):
        """Mark that the user has manually typed a name."""
        self._name_manually_set = True

    def _onBrowseProject(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder", ".")
        if folder:
            self.project_path_edit.setText(folder)

    def _onAccept(self):
        # Validate CMake options format
        opt_err = self.cmake_options_editor.validate()
        if opt_err:
            QMessageBox.critical(self, "Error", opt_err)
            return

        proj_path = self.project_path_edit.text().strip()
        inherit_proj = False
        if self.inherit_combo.currentIndex() > 0:
            for cb in self.attr_checkboxes:
                if cb.text() == "project_path" and cb.isChecked():
                    inherit_proj = True
                    break
        if not inherit_proj:
            if not os.path.isdir(proj_path):
                QMessageBox.critical(self, "Error", "Please select a valid project folder.")
                return
            if not os.path.exists(os.path.join(proj_path, "CMakeLists.txt")):
                QMessageBox.critical(self, "Error", "No CMakeLists.txt found in that folder.")
                return
        self.accept()

    # ------------------------------------------------------------------
    def getNodeData(self) -> tuple[str, list[str], str, int, list[str]]:
        """Return ``(node_name, cmake_options, project_path, inherit_index, inherit_attrs)``."""
        node_name = self.node_name_edit.text().strip()
        cmake_opts = self.cmake_options_editor.get_options()
        proj_path = self.project_path_edit.text().strip()
        inherit_index = self.inherit_combo.currentIndex() - 1
        attrs = [cb.text() for cb in self.attr_checkboxes if cb.isChecked()]
        return node_name, cmake_opts, proj_path, inherit_index, attrs

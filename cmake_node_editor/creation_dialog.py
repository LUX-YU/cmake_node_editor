import os

from dataclasses import fields
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QWidget, QFileDialog, QMessageBox, QDialogButtonBox,
    QScrollArea, QCheckBox, QComboBox
)

from .datas import NodeData

class NodeCreationDialog(QDialog):
    """
    A dialog that lets the user input:
      - A node name
      - Multiple CMake options
      - A target project folder (containing a CMakeLists.txt)
    """
    def __init__(self, parent=None, existing_nodes=None):
        super().__init__(parent)
        self.existing_nodes = existing_nodes if existing_nodes else []
        self.setWindowTitle("Create New Node")
        self.resize(500, 350)

        # UI elements for collecting input
        self.node_name_edit = QLineEdit()
        self.node_options_layout = QVBoxLayout()
        self.option_rows = []

        # Inheritance options
        self.inherit_combo = QComboBox()
        self.inherit_combo.addItem("None")
        for n in self.existing_nodes:
            self.inherit_combo.addItem(n.title())

        # Dynamically create checkboxes for inheritable attributes
        self.attr_checkboxes = []
        skip_fields = {"node_id", "title", "pos_x", "pos_y"}
        for f in fields(NodeData):
            if f.name in skip_fields:
                continue
            cb = QCheckBox(f.name)
            self.attr_checkboxes.append(cb)

        # Project path
        self.project_path_edit = QLineEdit()
        self.btn_browse_project = QPushButton("Browse Folder")
        self.btn_browse_project.clicked.connect(lambda: self.onBrowseProject())

        # Initially add one empty CMake option
        self.addOptionEdit()

        # "Add Option" button
        self.btn_add_option = QPushButton("Add CMake Option")
        self.btn_add_option.clicked.connect(lambda: self.addOptionEdit())

        # Build a form layout
        form = QFormLayout()
        form.addRow("Node Name:", self.node_name_edit)
        form.addRow("Inherit From:", self.inherit_combo)
        inherit_layout = QVBoxLayout()
        for cb in self.attr_checkboxes:
            inherit_layout.addWidget(cb)
        form.addRow("Copy Attributes:", inherit_layout)

        # Row for project path + browse button
        proj_path_layout = QHBoxLayout()
        proj_path_layout.addWidget(self.project_path_edit)
        proj_path_layout.addWidget(self.btn_browse_project)
        form.addRow("Project Path:", proj_path_layout)

        # CMake options widget with scrolling
        opts_widget = QWidget()
        opts_layout = QVBoxLayout(opts_widget)
        opts_layout.addLayout(self.node_options_layout)
        opts_layout.addWidget(self.btn_add_option)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(opts_widget)
        form.addRow("CMake Options:", scroll)

        # Dialog buttons (OK/Cancel)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        self.buttons.accepted.connect(self.onAccept)
        self.buttons.rejected.connect(self.reject)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addWidget(self.buttons)
        self.setLayout(main_layout)

    def addOptionEdit(self, text_value=""):
        """Add a new option row with a remove button."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit(text_value)
        btn_remove = QPushButton("Delete")

        row_layout.addWidget(edit)
        row_layout.addWidget(btn_remove)

        btn_remove.clicked.connect(lambda: self.removeOptionRow(row_widget))

        self.node_options_layout.addWidget(row_widget)
        self.option_rows.append((row_widget, edit))

    def removeOptionRow(self, row_widget):
        for i, (rw, le) in enumerate(self.option_rows):
            if rw == row_widget:
                self.node_options_layout.removeWidget(rw)
                rw.deleteLater()
                self.option_rows.pop(i)
                break

    def onBrowseProject(self):
        """
        Let the user pick a project folder. We check if it contains a CMakeLists.txt.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder", ".")
        if folder:
            self.project_path_edit.setText(folder)

    def onAccept(self):
        """
        When user clicks OK, ensure the project folder is valid and has CMakeLists.txt.
        """
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

            cmakelists_file = os.path.join(proj_path, "CMakeLists.txt")
            if not os.path.exists(cmakelists_file):
                QMessageBox.critical(self, "Error", "No CMakeLists.txt found in that folder.")
                return

        self.accept()

    def getNodeData(self) -> tuple[str, list[str], str, int, list[str]]:
        """
        Return (node_name, cmake_options, project_path, inherit_index, inherit_attrs) as a tuple.
        node_name  : str
        cmake_opts : list of str
        proj_path  : str
        inherit_attrs : list of str
        """
        node_name = self.node_name_edit.text().strip()
        cmake_opts = []
        for (_, ed) in self.option_rows:
            val = ed.text().strip()
            if val:
                cmake_opts.append(val)
        proj_path = self.project_path_edit.text().strip()
        inherit_index = self.inherit_combo.currentIndex() - 1
        attrs = [cb.text() for cb in self.attr_checkboxes if cb.isChecked()]
        return node_name, cmake_opts, proj_path, inherit_index, attrs

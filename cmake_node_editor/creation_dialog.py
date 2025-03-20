import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QWidget, QFileDialog, QMessageBox, QDialogButtonBox
)

class NodeCreationDialog(QDialog):
    """
    A dialog that lets the user input:
      - A node name
      - Multiple CMake options
      - A target project folder (containing a CMakeLists.txt)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Node")
        self.resize(500, 350)

        # UI elements for collecting input
        self.node_name_edit = QLineEdit()
        self.node_options_layout = QVBoxLayout()
        self.option_edits = []

        # Project path
        self.project_path_edit = QLineEdit()
        self.btn_browse_project = QPushButton("Browse Folder")
        self.btn_browse_project.clicked.connect(self.onBrowseProject)

        # Initially add one empty CMake option
        self.addOptionEdit()

        # "Add Option" button
        self.btn_add_option = QPushButton("Add CMake Option")
        self.btn_add_option.clicked.connect(self.addOptionEdit)

        # Build a form layout
        form = QFormLayout()
        form.addRow("Node Name:", self.node_name_edit)

        # Row for project path + browse button
        proj_path_layout = QHBoxLayout()
        proj_path_layout.addWidget(self.project_path_edit)
        proj_path_layout.addWidget(self.btn_browse_project)
        form.addRow("Project Path:", proj_path_layout)

        # CMake options widget
        opts_widget = QWidget()
        opts_layout = QVBoxLayout(opts_widget)
        opts_layout.addLayout(self.node_options_layout)
        opts_layout.addWidget(self.btn_add_option)
        form.addRow("CMake Options:", opts_widget)

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
        """
        Add a new QLineEdit to the CMake options layout, optionally pre-filled with 'text_value'.
        """
        edit = QLineEdit(text_value)
        self.node_options_layout.addWidget(edit)
        self.option_edits.append(edit)

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
        if not os.path.isdir(proj_path):
            QMessageBox.critical(self, "Error", "Please select a valid project folder.")
            return

        cmakelists_file = os.path.join(proj_path, "CMakeLists.txt")
        if not os.path.exists(cmakelists_file):
            QMessageBox.critical(self, "Error", "No CMakeLists.txt found in that folder.")
            return

        self.accept()

    def getNodeData(self):
        """
        Return (node_name, cmake_options, project_path) as a tuple.
        node_name  : str
        cmake_opts : list of str
        proj_path  : str
        """
        node_name = self.node_name_edit.text().strip()
        cmake_opts = []
        for ed in self.option_edits:
            val = ed.text().strip()
            if val:
                cmake_opts.append(val)
        proj_path = self.project_path_edit.text().strip()
        return node_name, cmake_opts, proj_path

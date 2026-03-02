"""
Node Creation Dialog — uses shared ``CMakeOptionsEditor``.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QFileDialog, QMessageBox, QDialogButtonBox,
    QCheckBox, QComboBox, QGroupBox,
)

from ..models.data_classes import BuildSettings
from ..constants import DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE, BUILD_SYSTEMS, BUILD_SYSTEM_LABELS
from .widgets.cmake_options_editor import CMakeOptionsEditor


class NodeCreationDialog(QDialog):
    """
    Dialog that lets the user create a new node with optional inheritance
    from an existing node.

    Inheritance is fully resolved inside :meth:`getNodeData` so that
    callers receive ready-to-use values.
    """

    # Node-level attributes available for copying
    _NODE_ATTRS = [
        ("cmake_options", "CMake Options"),
        ("code_before_build", "Pre-Configure Script"),
        ("code_after_install", "Post-Install Script"),
    ]

    # Individual BuildSettings fields
    _BS_ATTRS = [
        ("build_dir", "Build Directory"),
        ("install_dir", "Install Directory"),
        ("build_type", "Build Type"),
        ("prefix_path", "PREFIX_PATH"),
        ("toolchain_file", "Toolchain File"),
        ("generator", "Generator"),
        ("c_compiler", "C Compiler"),
        ("cxx_compiler", "C++ Compiler"),
    ]

    def __init__(self, parent=None, existing_nodes=None):
        super().__init__(parent)
        self.existing_nodes = existing_nodes if existing_nodes else []
        self.setWindowTitle("Create New Node")
        self.resize(600, 600)

        # -- Project path (auto-fills node name) --
        self.project_path_edit = QLineEdit()
        self.project_path_edit.textChanged.connect(self._onProjectPathChanged)
        self.btn_browse_project = QPushButton("Browse Folder")
        self.btn_browse_project.clicked.connect(self._onBrowseProject)

        # -- Node name --
        self.node_name_edit = QLineEdit()
        self._name_manually_set = False
        self.node_name_edit.textEdited.connect(self._onNameEdited)

        # -- Inherit From --
        self.inherit_combo = QComboBox()
        self.inherit_combo.addItem("None")
        for n in self.existing_nodes:
            self.inherit_combo.addItem(n.title())
        self.inherit_combo.currentIndexChanged.connect(self._onInheritChanged)

        # -- Copy Attributes (disabled until a source node is selected) --
        self._node_cbs: dict[str, QCheckBox] = {}
        self._bs_cbs: dict[str, QCheckBox] = {}

        self.copy_group = QGroupBox("Copy Attributes")
        copy_layout = QVBoxLayout(self.copy_group)

        for key, label in self._NODE_ATTRS:
            cb = QCheckBox(label)
            self._node_cbs[key] = cb
            copy_layout.addWidget(cb)

        bs_group = QGroupBox("Build Settings")
        bs_layout = QVBoxLayout(bs_group)
        for key, label in self._BS_ATTRS:
            cb = QCheckBox(label)
            self._bs_cbs[key] = cb
            bs_layout.addWidget(cb)
        copy_layout.addWidget(bs_group)

        self.copy_group.setEnabled(False)

        # -- Build System --
        self.combo_build_system = QComboBox()
        for key in BUILD_SYSTEMS:
            self.combo_build_system.addItem(BUILD_SYSTEM_LABELS[key], key)
        self.combo_build_system.currentIndexChanged.connect(self._onBuildSystemChanged)

        # -- CMake options --
        self.cmake_options_editor = CMakeOptionsEditor()

        # -- Form layout --
        form = QFormLayout()

        proj_path_layout = QHBoxLayout()
        proj_path_layout.addWidget(self.project_path_edit)
        proj_path_layout.addWidget(self.btn_browse_project)
        form.addRow("Project Path:", proj_path_layout)

        form.addRow("Node Name:", self.node_name_edit)
        form.addRow("Build System:", self.combo_build_system)
        form.addRow("Inherit From:", self.inherit_combo)
        form.addRow(self.copy_group)
        self._cmake_options_row_label = QLabel("CMake Options:")
        form.addRow(self._cmake_options_row_label, self.cmake_options_editor)

        # -- OK / Cancel --
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
    # Slots
    # ------------------------------------------------------------------

    def _onBuildSystemChanged(self, _index: int):
        """Show / hide CMake-specific widgets based on build system."""
        is_cmake = self.combo_build_system.currentData() == "cmake"
        self.cmake_options_editor.setVisible(is_cmake)
        self._cmake_options_row_label.setVisible(is_cmake)

    def _onInheritChanged(self, index: int):
        """Enable / disable the copy-attributes group."""
        self.copy_group.setEnabled(index > 0)

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
        is_cmake = self.combo_build_system.currentData() == "cmake"

        if is_cmake:
            opt_err = self.cmake_options_editor.validate()
            if opt_err:
                QMessageBox.critical(self, "Error", opt_err)
                return

        proj_path = self.project_path_edit.text().strip()
        if not os.path.isdir(proj_path):
            QMessageBox.critical(self, "Error", "Please select a valid project folder.")
            return
        if is_cmake and not os.path.exists(os.path.join(proj_path, "CMakeLists.txt")):
            QMessageBox.critical(self, "Error", "No CMakeLists.txt found in that folder.")
            return
        self.accept()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _base_node(self):
        """Return the selected source node, or *None*."""
        idx = self.inherit_combo.currentIndex() - 1
        if 0 <= idx < len(self.existing_nodes):
            return self.existing_nodes[idx]
        return None

    def getNodeData(
        self,
    ) -> tuple[str, list[str], str, BuildSettings | None, str, str, str]:
        """Return ``(node_name, cmake_options, project_path, build_settings,
        code_before, code_after, build_system)``.

        All inheritance is resolved internally — callers receive ready-to-use
        values.
        """
        node_name = self.node_name_edit.text().strip()
        cmake_opts = self.cmake_options_editor.get_options()
        proj_path = self.project_path_edit.text().strip()
        code_before = ""
        code_after = ""
        bs: BuildSettings | None = None

        base = self._base_node()
        if base:
            if self._node_cbs["cmake_options"].isChecked():
                cmake_opts = list(base.cmakeOptions())
            if self._node_cbs["code_before_build"].isChecked():
                code_before = base.codeBeforeBuild()
            if self._node_cbs["code_after_install"].isChecked():
                code_after = base.codeAfterInstall()

            # Build settings — merge only checked fields over defaults
            checked_bs = [k for k, cb in self._bs_cbs.items() if cb.isChecked()]
            if checked_bs:
                src = base.buildSettings()
                bs = BuildSettings(
                    build_dir=src.build_dir if "build_dir" in checked_bs else DEFAULT_BUILD_DIR,
                    install_dir=src.install_dir if "install_dir" in checked_bs else DEFAULT_INSTALL_DIR,
                    build_type=src.build_type if "build_type" in checked_bs else DEFAULT_BUILD_TYPE,
                    prefix_path=src.prefix_path if "prefix_path" in checked_bs else DEFAULT_INSTALL_DIR,
                    toolchain_file=src.toolchain_file if "toolchain_file" in checked_bs else "",
                    generator=src.generator if "generator" in checked_bs else "",
                    c_compiler=src.c_compiler if "c_compiler" in checked_bs else "",
                    cxx_compiler=src.cxx_compiler if "cxx_compiler" in checked_bs else "",
                )

        build_system = self.combo_build_system.currentData()
        return node_name, cmake_opts, proj_path, bs, code_before, code_after, build_system

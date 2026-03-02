"""
Node Creation Dialog — uses shared ``CMakeOptionsEditor``.

The *Build System* selector is presented first and drives the rest of the
UI: which widgets are visible, which nodes can be inherited from, and
which copy-attribute checkboxes are shown.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QFileDialog, QMessageBox, QDialogButtonBox,
    QCheckBox, QComboBox, QGroupBox, QLabel,
)

from ..models.data_classes import BuildSettings, CustomCommands
from ..constants import (
    DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE,
    BUILD_SYSTEMS, BUILD_SYSTEM_LABELS,
)
from .widgets.cmake_options_editor import CMakeOptionsEditor


class NodeCreationDialog(QDialog):
    """
    Dialog that lets the user create a new node with optional inheritance
    from an existing node.

    Inheritance is fully resolved inside :meth:`getNodeData` so that
    callers receive ready-to-use values.
    """

    # Shared attributes (available for every build system)
    _SHARED_ATTRS = [
        ("code_before_build", "Pre-Configure Script"),
        ("code_after_install", "Post-Install Script"),
    ]

    # CMake-only node-level attributes
    _CMAKE_ATTRS = [
        ("cmake_options", "CMake Options"),
    ]

    # Custom-script-only node-level attributes
    _CUSTOM_ATTRS = [
        ("custom_commands", "Custom Commands (configure / build / install)"),
    ]

    # Build-settings fields shared across all build systems
    _BS_SHARED = [
        ("build_dir", "Build Directory"),
        ("install_dir", "Install Directory"),
        ("build_type", "Build Type"),
    ]

    # Build-settings fields only relevant to CMake
    _BS_CMAKE_ONLY = [
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

        self._buildUI()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _buildUI(self):
        form = QFormLayout()

        # ── 1. Build System (drives everything below) ──
        self.combo_build_system = QComboBox()
        for key in BUILD_SYSTEMS:
            self.combo_build_system.addItem(BUILD_SYSTEM_LABELS[key], key)
        self.combo_build_system.currentIndexChanged.connect(self._onBuildSystemChanged)
        form.addRow("Build System:", self.combo_build_system)

        # ── 2. Project path ──
        self.project_path_edit = QLineEdit()
        self.project_path_edit.textChanged.connect(self._onProjectPathChanged)
        self.btn_browse_project = QPushButton("Browse Folder")
        self.btn_browse_project.clicked.connect(self._onBrowseProject)

        proj_path_layout = QHBoxLayout()
        proj_path_layout.addWidget(self.project_path_edit)
        proj_path_layout.addWidget(self.btn_browse_project)
        form.addRow("Project Path:", proj_path_layout)

        # ── 3. Node name ──
        self.node_name_edit = QLineEdit()
        self._name_manually_set = False
        self.node_name_edit.textEdited.connect(self._onNameEdited)
        form.addRow("Node Name:", self.node_name_edit)

        # ── 4. Inherit From (filtered by build system) ──
        self.inherit_combo = QComboBox()
        self.inherit_combo.currentIndexChanged.connect(self._onInheritChanged)
        form.addRow("Inherit From:", self.inherit_combo)

        # ── 5. Copy Attributes ──
        self._all_cbs: dict[str, QCheckBox] = {}

        self.copy_group = QGroupBox("Copy Attributes")
        copy_layout = QVBoxLayout(self.copy_group)

        # Shared
        for key, label in self._SHARED_ATTRS:
            cb = QCheckBox(label)
            self._all_cbs[key] = cb
            copy_layout.addWidget(cb)

        # CMake-only node attrs
        for key, label in self._CMAKE_ATTRS:
            cb = QCheckBox(label)
            self._all_cbs[key] = cb
            copy_layout.addWidget(cb)

        # Custom-script-only node attrs
        for key, label in self._CUSTOM_ATTRS:
            cb = QCheckBox(label)
            self._all_cbs[key] = cb
            copy_layout.addWidget(cb)

        # Build Settings sub-group
        self.bs_group = QGroupBox("Build Settings")
        bs_layout = QVBoxLayout(self.bs_group)
        for key, label in self._BS_SHARED + self._BS_CMAKE_ONLY:
            cb = QCheckBox(label)
            self._all_cbs[key] = cb
            bs_layout.addWidget(cb)
        copy_layout.addWidget(self.bs_group)

        self.copy_group.setEnabled(False)
        form.addRow(self.copy_group)

        # ── 6. CMake Options (only for cmake) ──
        self._cmake_options_label = QLabel("CMake Options:")
        self.cmake_options_editor = CMakeOptionsEditor()
        form.addRow(self._cmake_options_label, self.cmake_options_editor)

        # ── OK / Cancel ──
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self._onAccept)
        self.buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addWidget(self.buttons)

        # Initial state
        self._refreshForBuildSystem()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _currentBuildSystem(self) -> str:
        return self.combo_build_system.currentData() or "cmake"

    def _onBuildSystemChanged(self, _index: int):
        """Rebuild Inherit-From list and toggle visibility of widgets."""
        self._refreshForBuildSystem()

    def _refreshForBuildSystem(self):
        """Synchronise all UI elements with the current build-system choice."""
        bs = self._currentBuildSystem()
        is_cmake = (bs == "cmake")

        # CMake Options editor
        self.cmake_options_editor.setVisible(is_cmake)
        self._cmake_options_label.setVisible(is_cmake)

        # Rebuild Inherit-From: only same-build-system nodes
        prev_text = self.inherit_combo.currentText()
        self.inherit_combo.blockSignals(True)
        self.inherit_combo.clear()
        self.inherit_combo.addItem("None")
        self._filtered_nodes: list = []
        for n in self.existing_nodes:
            if n.buildSystem() == bs:
                self.inherit_combo.addItem(n.title())
                self._filtered_nodes.append(n)
        # Try to restore previous selection
        idx = self.inherit_combo.findText(prev_text)
        self.inherit_combo.setCurrentIndex(max(idx, 0))
        self.inherit_combo.blockSignals(False)
        self._onInheritChanged(self.inherit_combo.currentIndex())

        # Toggle copy-attribute checkboxes visibility
        cmake_keys = {k for k, _ in self._CMAKE_ATTRS}
        custom_keys = {k for k, _ in self._CUSTOM_ATTRS}
        cmake_bs_keys = {k for k, _ in self._BS_CMAKE_ONLY}

        for key, cb in self._all_cbs.items():
            if key in cmake_keys:
                cb.setVisible(is_cmake)
            elif key in custom_keys:
                cb.setVisible(not is_cmake)
            elif key in cmake_bs_keys:
                cb.setVisible(is_cmake)
            # else: shared — always visible

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
        is_cmake = self._currentBuildSystem() == "cmake"

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
        """Return the selected source node (filtered list), or *None*."""
        idx = self.inherit_combo.currentIndex() - 1
        if 0 <= idx < len(self._filtered_nodes):
            return self._filtered_nodes[idx]
        return None

    def getNodeData(
        self,
    ) -> tuple[str, list[str], str, BuildSettings | None, str, str, str, CustomCommands | None]:
        """Return ``(node_name, cmake_options, project_path, build_settings,
        code_before, code_after, build_system, custom_commands)``.

        All inheritance is resolved internally — callers receive ready-to-use
        values.
        """
        node_name = self.node_name_edit.text().strip()
        cmake_opts = self.cmake_options_editor.get_options()
        proj_path = self.project_path_edit.text().strip()
        code_before = ""
        code_after = ""
        bs: BuildSettings | None = None
        custom_cmds: CustomCommands | None = None
        build_system = self._currentBuildSystem()

        base = self._base_node()
        if base:
            # Shared attrs
            if self._all_cbs.get("code_before_build", _NullCB).isChecked():
                code_before = base.codeBeforeBuild()
            if self._all_cbs.get("code_after_install", _NullCB).isChecked():
                code_after = base.codeAfterInstall()

            if build_system == "cmake":
                if self._all_cbs.get("cmake_options", _NullCB).isChecked():
                    cmake_opts = list(base.cmakeOptions())
            else:
                if self._all_cbs.get("custom_commands", _NullCB).isChecked():
                    src_cc = base.customCommands()
                    if src_cc:
                        custom_cmds = CustomCommands(
                            configure_script=src_cc.configure_script,
                            build_script=src_cc.build_script,
                            install_script=src_cc.install_script,
                        )

            # Build settings — merge only checked fields over defaults
            bs_keys_all = [k for k, _ in self._BS_SHARED + self._BS_CMAKE_ONLY]
            checked_bs = [k for k in bs_keys_all if self._all_cbs.get(k, _NullCB).isChecked()]
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

        return node_name, cmake_opts, proj_path, bs, code_before, code_after, build_system, custom_cmds


class _NullCB:
    """Sentinel so `dict.get(key, _NullCB).isChecked()` always returns False."""
    @staticmethod
    def isChecked() -> bool:
        return False

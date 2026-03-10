"""
Node Creation Dialog — **strategy-driven** layout.

The *Build System* selector is presented first and drives the rest of the
UI: which nodes can be inherited from, which copy-attribute checkboxes
are shown, and which creation-time validation runs.

Adding a new build system requires **zero changes** in this file — all
labels, checkboxes, and validation are derived from the strategy registry.
"""

import os
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QFileDialog, QMessageBox, QDialogButtonBox,
    QCheckBox, QComboBox, QGroupBox,
)

from ..models.data_classes import BuildSettings
from ..constants import DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE
from ..services.build_strategies import (
    get_strategy, STRATEGY_NAMES, STRATEGY_LABELS,
)


# BuildSettings field metadata — independent of any strategy
_ALL_BS_FIELDS: list[tuple[str, str]] = [
    ("build_dir", "Build Directory"),
    ("install_dir", "Install Directory"),
    ("build_type", "Build Type"),
    ("prefix_path", "Prefix Path"),
    ("toolchain_file", "Toolchain File"),
    ("generator", "Generator"),
    ("c_compiler", "C Compiler"),
    ("cxx_compiler", "C++ Compiler"),
]

_BS_DEFAULTS: dict[str, str] = {
    "build_dir": DEFAULT_BUILD_DIR,
    "install_dir": DEFAULT_INSTALL_DIR,
    "build_type": DEFAULT_BUILD_TYPE,
    "prefix_path": DEFAULT_INSTALL_DIR,
    "toolchain_file": "",
    "generator": "",
    "c_compiler": "",
    "cxx_compiler": "",
}


@dataclass
class CreationResult:
    """Return value of :meth:`NodeCreationDialog.getResult`."""
    node_name: str
    project_path: str
    build_system: str
    build_settings: BuildSettings | None = None
    code_before_build: str = ""
    code_after_install: str = ""
    # Deferred strategy-specific inheritance — caller delegates to strategy
    inherit_source: object = None   # NodeItem | None
    inherit_keys: set[str] = field(default_factory=set)


class NodeCreationDialog(QDialog):
    """
    Dialog that lets the user create a new node with optional inheritance
    from an existing node.

    Shared inheritance (scripts, build settings) is resolved in
    :meth:`getResult`.  Strategy-specific inheritance (e.g. cmake_options,
    custom_commands) is deferred to the caller via ``strategy.copy_node_data``.
    """

    # Shared attributes (available for every build system)
    _SHARED_ATTRS = [
        ("code_before_build", "Pre-Configure Script"),
        ("code_after_install", "Post-Install Script"),
    ]

    def __init__(self, parent=None, existing_nodes=None):
        super().__init__(parent)
        self.existing_nodes = existing_nodes if existing_nodes else []
        self.setWindowTitle("Create New Node")
        self.resize(600, 600)

        self._filtered_nodes: list = []
        self._buildUI()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _buildUI(self):
        form = QFormLayout()

        # ── 1. Build System (drives everything below) ──
        self.combo_build_system = QComboBox()
        for name in STRATEGY_NAMES:
            self.combo_build_system.addItem(STRATEGY_LABELS[name], name)
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

        # ── 5. Copy Attributes group ──
        self._shared_cbs: dict[str, QCheckBox] = {}
        self._strategy_cbs: dict[str, QCheckBox] = {}
        self._bs_cbs: dict[str, QCheckBox] = {}

        self.copy_group = QGroupBox("Copy Attributes")
        self._copy_layout = QVBoxLayout(self.copy_group)

        # Shared attrs (always shown)
        for key, label in self._SHARED_ATTRS:
            cb = QCheckBox(label)
            self._shared_cbs[key] = cb
            self._copy_layout.addWidget(cb)

        # Strategy-specific attrs — placeholder, populated dynamically
        self._strategy_cb_widgets: list[QCheckBox] = []

        # Build Settings sub-group
        self.bs_group = QGroupBox("Build Settings")
        self._bs_layout = QVBoxLayout(self.bs_group)
        for key, label in _ALL_BS_FIELDS:
            cb = QCheckBox(label)
            self._bs_cbs[key] = cb
            self._bs_layout.addWidget(cb)
        self._copy_layout.addWidget(self.bs_group)

        self.copy_group.setVisible(False)
        form.addRow(self.copy_group)

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
        return self.combo_build_system.currentData() or STRATEGY_NAMES[0]

    def _currentStrategy(self):
        return get_strategy(self._currentBuildSystem())

    def _onBuildSystemChanged(self, _index: int):
        self._refreshForBuildSystem()

    def _refreshForBuildSystem(self):
        """Synchronise all UI elements with the current build-system choice."""
        strategy = self._currentStrategy()

        # -- Rebuild Inherit-From: only same-build-system nodes --
        prev_text = self.inherit_combo.currentText()
        self.inherit_combo.blockSignals(True)
        self.inherit_combo.clear()
        self.inherit_combo.addItem("None")
        self._filtered_nodes = []
        for n in self.existing_nodes:
            if n.buildSystem() == strategy.name:
                self.inherit_combo.addItem(n.title())
                self._filtered_nodes.append(n)
        idx = self.inherit_combo.findText(prev_text)
        self.inherit_combo.setCurrentIndex(max(idx, 0))
        self.inherit_combo.blockSignals(False)
        self._onInheritChanged(self.inherit_combo.currentIndex())

        # -- Rebuild strategy-specific copy-attribute checkboxes --
        for cb in self._strategy_cb_widgets:
            self._copy_layout.removeWidget(cb)
            cb.deleteLater()
        self._strategy_cb_widgets.clear()
        self._strategy_cbs.clear()

        bs_group_idx = self._copy_layout.indexOf(self.bs_group)
        for key, label in strategy.copyable_node_attrs():
            cb = QCheckBox(label)
            self._strategy_cbs[key] = cb
            self._strategy_cb_widgets.append(cb)
            self._copy_layout.insertWidget(bs_group_idx, cb)
            bs_group_idx += 1

        # -- Toggle Build Settings field visibility --
        relevant = set(strategy.relevant_build_setting_keys())
        for key, cb in self._bs_cbs.items():
            cb.setVisible(key in relevant)

    def _onInheritChanged(self, index: int):
        visible = index > 0
        self.copy_group.setVisible(visible)
        if visible:
            for cb in self._bs_cbs.values():
                if cb.isVisible():
                    cb.setChecked(True)

    def _onProjectPathChanged(self, text: str):
        if self._name_manually_set:
            return
        text = text.strip().rstrip('/').rstrip('\\')
        if text:
            basename = os.path.basename(text)
            if basename:
                self.node_name_edit.setText(basename)

    def _onNameEdited(self, _text: str):
        self._name_manually_set = True

    def _onBrowseProject(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder", ".")
        if folder:
            self.project_path_edit.setText(folder)

    def _onAccept(self):
        proj_path = self.project_path_edit.text().strip()
        if not os.path.isdir(proj_path):
            QMessageBox.critical(self, "Error", "Please select a valid project folder.")
            return

        # Delegate creation-time validation to the strategy
        strategy = self._currentStrategy()
        dir_err = strategy.validate_project_dir(proj_path)
        if dir_err:
            QMessageBox.critical(self, "Error", dir_err)
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

    def getResult(self) -> CreationResult:
        """Return a :class:`CreationResult` with all dialog values.

        Shared-attribute inheritance (``code_before_build``,
        ``code_after_install``) and ``BuildSettings`` field copying are
        resolved here.  Strategy-specific copying is deferred to the
        caller via ``inherit_source`` + ``inherit_keys``.
        """
        strategy = self._currentStrategy()

        result = CreationResult(
            node_name=self.node_name_edit.text().strip(),
            project_path=self.project_path_edit.text().strip(),
            build_system=self._currentBuildSystem(),
        )

        base = self._base_node()
        if base:
            # Shared attrs
            if self._shared_cbs.get("code_before_build", _NullCB).isChecked():
                result.code_before_build = base.codeBeforeBuild()
            if self._shared_cbs.get("code_after_install", _NullCB).isChecked():
                result.code_after_install = base.codeAfterInstall()

            # Build settings — merge only checked, relevant fields
            relevant = set(strategy.relevant_build_setting_keys())
            checked = [k for k, cb in self._bs_cbs.items()
                       if k in relevant and cb.isChecked()]
            if checked:
                src = base.buildSettings()
                merged: dict[str, str] = {}
                for key, _ in _ALL_BS_FIELDS:
                    if key in checked:
                        merged[key] = getattr(src, key)
                    else:
                        merged[key] = _BS_DEFAULTS[key]
                result.build_settings = BuildSettings(**merged)

            # Strategy-specific keys → deferred to caller
            selected_keys = {k for k, cb in self._strategy_cbs.items() if cb.isChecked()}
            if selected_keys:
                result.inherit_source = base
                result.inherit_keys = selected_keys

        return result


class _NullCB:
    """Sentinel so ``dict.get(key, _NullCB).isChecked()`` always returns False."""
    @staticmethod
    def isChecked() -> bool:
        return False

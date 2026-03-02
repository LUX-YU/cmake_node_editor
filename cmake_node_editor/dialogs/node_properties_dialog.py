"""
Node Properties Dialog — **strategy-driven** layout.

The Build System combo populates the ``QStackedWidget`` dynamically from
the strategy registry.  Each strategy provides its own form widget via
:meth:`BuildStrategy.create_properties_form`, so adding a new build
system requires **zero changes** in this file.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QWidget,
    QLabel, QLineEdit, QPlainTextEdit,
    QDialogButtonBox, QMessageBox, QComboBox, QStackedWidget,
)

from ..views.graphics_items import NodeItem
from ..services.build_strategies import get_strategy, STRATEGY_NAMES, STRATEGY_LABELS


class NodePropertiesDialog(QDialog):
    """Modal dialog for editing a single :class:`NodeItem`'s properties."""

    def __init__(self, node_item: NodeItem, parent=None):
        super().__init__(parent)
        self.node_item = node_item
        self.setWindowTitle(f"Edit Node - {node_item.title()}")
        self.resize(700, 800)

        # maps strategy name → (stack index, form widget)
        self._form_map: dict[str, tuple[int, QWidget]] = {}

        self._buildUI()
        self.loadFromNode(node_item)

    # ------------------------------------------------------------------
    def _buildUI(self):
        layout = QVBoxLayout(self)

        # Project path
        form_proj = QFormLayout()
        self.edit_node_project_path = QLineEdit()
        form_proj.addRow("Project Path:", self.edit_node_project_path)
        layout.addLayout(form_proj)

        # Name
        form_name = QFormLayout()
        self.edit_node_name = QLineEdit()
        form_name.addRow("Name:", self.edit_node_name)
        layout.addLayout(form_name)

        # Build System selector
        form_bs = QFormLayout()
        self.combo_build_system = QComboBox()
        for name in STRATEGY_NAMES:
            self.combo_build_system.addItem(STRATEGY_LABELS[name], name)
        self.combo_build_system.currentIndexChanged.connect(self._onBuildSystemChanged)
        form_bs.addRow("Build System:", self.combo_build_system)
        layout.addLayout(form_bs)

        # Strategy-specific forms in a stacked widget
        self.stack = QStackedWidget()
        for idx, name in enumerate(STRATEGY_NAMES):
            strategy = get_strategy(name)
            form = strategy.create_properties_form()
            self.stack.addWidget(form)
            self._form_map[name] = (idx, form)
        layout.addWidget(self.stack)

        # Shared scripts
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

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _onBuildSystemChanged(self, _index: int):
        bs_name = self.combo_build_system.currentData()
        if bs_name in self._form_map:
            self.stack.setCurrentIndex(self._form_map[bs_name][0])

    def _onAccept(self):
        form = self._currentForm()
        if hasattr(form, "validate"):
            err = form.validate()
            if err:
                QMessageBox.warning(self, "Validation Error", err)
                return
        self.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _currentBuildSystem(self) -> str:
        return self.combo_build_system.currentData()

    def _currentForm(self) -> QWidget:
        return self._form_map[self._currentBuildSystem()][1]

    # ------------------------------------------------------------------
    def loadFromNode(self, node: NodeItem):
        self.edit_node_name.setText(node.title())
        self.edit_node_project_path.setText(node.projectPath())

        # Build system combo
        bs_key = node.buildSystem()
        for i in range(self.combo_build_system.count()):
            if self.combo_build_system.itemData(i) == bs_key:
                self.combo_build_system.setCurrentIndex(i)
                break

        # Load ALL forms so switching build system keeps data intact
        for name, (_idx, form) in self._form_map.items():
            if hasattr(form, "load_from_node"):
                form.load_from_node(node)

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
        node.setProjectPath(self.edit_node_project_path.text().strip())
        node.setBuildSystem(self._currentBuildSystem())

        # Delegate to the active strategy form
        form = self._currentForm()
        if hasattr(form, "apply_to_node"):
            form.apply_to_node(node)

        node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
        node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

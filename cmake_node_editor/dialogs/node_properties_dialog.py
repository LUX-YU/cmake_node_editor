"""
Node Properties Dialog — uses shared ``BuildSettingsForm`` and ``CMakeOptionsEditor``.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit,
    QDialogButtonBox, QMessageBox, QComboBox, QStackedWidget,
)

from ..models.data_classes import BuildSettings, CustomCommands
from ..views.graphics_items import NodeItem
from ..constants import BUILD_SYSTEMS, BUILD_SYSTEM_LABELS
from .widgets.build_settings_form import BuildSettingsForm
from .widgets.cmake_options_editor import CMakeOptionsEditor
from .widgets.custom_commands_form import CustomCommandsForm


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

        # Build System selector
        form_bs = QFormLayout()
        self.combo_build_system = QComboBox()
        for key in BUILD_SYSTEMS:
            self.combo_build_system.addItem(BUILD_SYSTEM_LABELS[key], key)
        self.combo_build_system.currentIndexChanged.connect(self._onBuildSystemChanged)
        form_bs.addRow("Build System:", self.combo_build_system)
        layout.addLayout(form_bs)

        # Stacked widget: page 0 = CMake, page 1 = Custom Script
        self.stack = QStackedWidget()

        # -- CMake page --
        cmake_page = QWidget()
        cmake_layout = QVBoxLayout(cmake_page)
        cmake_layout.setContentsMargins(0, 0, 0, 0)
        self.cmake_options_editor = CMakeOptionsEditor()
        cmake_layout.addWidget(self.cmake_options_editor)
        self.build_settings_form = BuildSettingsForm()
        cmake_layout.addWidget(self.build_settings_form)
        self.stack.addWidget(cmake_page)

        # -- Custom Script page --
        custom_page = QWidget()
        custom_layout = QVBoxLayout(custom_page)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_commands_form = CustomCommandsForm()
        custom_layout.addWidget(self.custom_commands_form)
        self.stack.addWidget(custom_page)

        layout.addWidget(self.stack)

        # Scripts (shared — pre-build / post-install Python scripts)
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

    def _onBuildSystemChanged(self, index: int):
        self.stack.setCurrentIndex(index)

    def _onAccept(self):
        if self._currentBuildSystem() == "cmake":
            opt_err = self.cmake_options_editor.validate()
            if opt_err:
                QMessageBox.warning(self, "Invalid CMake Options", opt_err)
                return
        self.accept()

    def _currentBuildSystem(self) -> str:
        return self.combo_build_system.currentData()

    # ------------------------------------------------------------------
    def loadFromNode(self, node: NodeItem):
        self.edit_node_name.setText(node.title())
        self.edit_node_project_path.setText(node.projectPath())

        # Set build system combo
        bs_key = node.buildSystem()
        for i in range(self.combo_build_system.count()):
            if self.combo_build_system.itemData(i) == bs_key:
                self.combo_build_system.setCurrentIndex(i)
                break

        self.cmake_options_editor.set_options(node.cmakeOptions())
        self.build_settings_form.load_from_settings(node.buildSettings())
        self.custom_commands_form.load_from(node.customCommands())

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

        if self._currentBuildSystem() == "cmake":
            node.setCMakeOptions(self.cmake_options_editor.get_options())
            node.setBuildSettings(self.build_settings_form.to_settings())
        else:
            node.setCustomCommands(self.custom_commands_form.to_commands())

        node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
        node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

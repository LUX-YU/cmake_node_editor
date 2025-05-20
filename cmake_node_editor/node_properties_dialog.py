# Node Properties Dialog

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea, QWidget,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QComboBox,
    QDialogButtonBox, QMessageBox
)

from .datas import BuildSettings
from .node_scene import NodeItem


class NodePropertiesDialog(QDialog):
    """Modal dialog for editing a NodeItem's properties."""

    def __init__(self, node_item: NodeItem, parent=None):
        super().__init__(parent)
        self.node_item = node_item
        self.setWindowTitle(f"Edit Node - {node_item.title()}")
        self.resize(600, 700)

        self.cmake_option_rows = []
        self._buildUI()
        self.loadFromNode(node_item)

    # ------------------------------------------------------------------
    def _buildUI(self):
        layout = QVBoxLayout(self)

        form_name = QFormLayout()
        self.edit_node_name = QLineEdit()
        form_name.addRow("Name:", self.edit_node_name)
        layout.addLayout(form_name)

        form_proj = QFormLayout()
        self.edit_node_project_path = QLineEdit()
        form_proj.addRow("Project Path:", self.edit_node_project_path)
        layout.addLayout(form_proj)

        self.cmake_option_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_add_cmake_opt = QPushButton("Add CMake Option")
        self.btn_add_cmake_opt.clicked.connect(self.onAddCMakeOptionField)
        btn_row.addWidget(self.btn_add_cmake_opt)
        self.cmake_option_layout.addLayout(btn_row)

        option_container = QWidget()
        option_container.setLayout(self.cmake_option_layout)
        option_scroll = QScrollArea()
        option_scroll.setWidgetResizable(True)
        option_scroll.setWidget(option_container)
        layout.addWidget(option_scroll)

        form_build = QFormLayout()
        self.edit_build_dir = QLineEdit(os.path.join(os.getcwd(), "build"))
        form_build.addRow("Build Directory:", self.edit_build_dir)

        self.combo_build_type = QComboBox()
        self.combo_build_type.addItems(["Debug", "Release", "RelWithDebInfo", "MinSizeRel"])
        form_build.addRow("Build Type:", self.combo_build_type)

        self.edit_install_dir = QLineEdit(os.path.join(os.getcwd(), "install"))
        form_build.addRow("Install Directory:", self.edit_install_dir)

        self.edit_prefix_path = QLineEdit(os.path.join(os.getcwd(), "install"))
        form_build.addRow("PREFIX_PATH:", self.edit_prefix_path)

        self.edit_toolchain = QLineEdit()
        form_build.addRow("Toolchain File:", self.edit_toolchain)

        self.combo_generator = QComboBox()
        self.combo_generator.addItem("Default (not specified)")
        self.combo_generator.addItems([
            "Visual Studio 17 2022", "Visual Studio 16 2019",
            "Ninja", "Unix Makefiles",
        ])
        form_build.addRow("CMake Generator:", self.combo_generator)

        self.edit_c_compiler = QLineEdit()
        form_build.addRow("C Compiler:", self.edit_c_compiler)

        self.edit_cxx_compiler = QLineEdit()
        form_build.addRow("C++ Compiler:", self.edit_cxx_compiler)

        layout.addLayout(form_build)

        layout.addWidget(QLabel("Pre-Build Script (py_code_before_build):"))
        self.edit_py_before = QPlainTextEdit()
        layout.addWidget(self.edit_py_before)

        layout.addWidget(QLabel("Post-Install Script (py_code_after_install):"))
        self.edit_py_after = QPlainTextEdit()
        layout.addWidget(self.edit_py_after)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    def createOptionRow(self, text_value=""):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(text_value)
        btn_delete = QPushButton("Delete")
        row_layout.addWidget(line_edit)
        row_layout.addWidget(btn_delete)

        btn_delete.clicked.connect(lambda: self.removeOptionRow(row_widget))
        return row_widget, line_edit

    def removeOptionRow(self, row_widget):
        for i, (rw, le) in enumerate(self.cmake_option_rows):
            if rw == row_widget:
                self.cmake_option_layout.removeWidget(rw)
                rw.deleteLater()
                self.cmake_option_rows.pop(i)
                break

    def onAddCMakeOptionField(self):
        row_widget, line_edit = self.createOptionRow("")
        self.cmake_option_rows.append((row_widget, line_edit))
        self.cmake_option_layout.insertWidget(self.cmake_option_layout.count() - 1, row_widget)

    # ------------------------------------------------------------------
    def loadFromNode(self, node: NodeItem):
        self.edit_node_name.setText(node.title())
        self.edit_node_project_path.setText(node.projectPath())

        for opt in node.cmakeOptions():
            row_widget, line_edit = self.createOptionRow(opt)
            self.cmake_option_rows.append((row_widget, line_edit))
            self.cmake_option_layout.insertWidget(len(self.cmake_option_rows) - 1, row_widget)

        bs = node.buildSettings()
        self.edit_build_dir.setText(bs.build_dir)
        idx_bt = self.combo_build_type.findText(bs.build_type)
        if idx_bt >= 0:
            self.combo_build_type.setCurrentIndex(idx_bt)
        else:
            self.combo_build_type.setCurrentText(bs.build_type)
        self.edit_install_dir.setText(bs.install_dir)
        self.edit_prefix_path.setText(bs.prefix_path)
        self.edit_toolchain.setText(bs.toolchain_file)
        if bs.generator:
            gen_idx = self.combo_generator.findText(bs.generator)
            if gen_idx >= 0:
                self.combo_generator.setCurrentIndex(gen_idx)
            else:
                self.combo_generator.setCurrentText(bs.generator)
        else:
            self.combo_generator.setCurrentIndex(0)
        self.edit_c_compiler.setText(bs.c_compiler)
        self.edit_cxx_compiler.setText(bs.cxx_compiler)
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

        new_opts = []
        for (_, line_edit) in self.cmake_option_rows:
            val = line_edit.text().strip()
            if val:
                new_opts.append(val)
        node.setCMakeOptions(new_opts)
        node.setProjectPath(self.edit_node_project_path.text().strip())

        generator = "" if self.combo_generator.currentIndex() == 0 else self.combo_generator.currentText()
        bs = BuildSettings(
            build_dir=self.edit_build_dir.text().strip(),
            install_dir=self.edit_install_dir.text().strip(),
            build_type=self.combo_build_type.currentText(),
            prefix_path=self.edit_prefix_path.text().strip(),
            toolchain_file=self.edit_toolchain.text().strip(),
            generator=generator,
            c_compiler=self.edit_c_compiler.text().strip(),
            cxx_compiler=self.edit_cxx_compiler.text().strip(),
        )
        node.setBuildSettings(bs)
        node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
        node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

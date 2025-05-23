import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea, QWidget,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QComboBox, QCheckBox,
    QDialogButtonBox, QListWidget, QListWidgetItem, QMessageBox,
    QSplitter
)

from .datas import BuildSettings
from .node_scene import NodeItem


class BatchEditDialog(QDialog):
    """Dialog for editing multiple nodes at once."""

    def __init__(self, nodes: list[NodeItem], parent=None):
        super().__init__(parent)
        self.nodes = nodes
        self.setWindowTitle("Batch Edit Nodes")
        self.resize(600, 700)

        self.cmake_option_rows = []
        self._buildUI()
        if nodes:
            self.loadFromNode(nodes[0])

    # ------------------------------------------------------------------
    def _buildUI(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        node_widget = QWidget()
        node_layout = QVBoxLayout(node_widget)
        node_layout.addWidget(QLabel("Select Nodes:"))
        self.list_nodes = QListWidget()
        for n in self.nodes:
            item = QListWidgetItem(f"{n.title()} (ID={n.id()})")
            item.setData(Qt.ItemDataRole.UserRole, n)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_nodes.addItem(item)
        node_layout.addWidget(self.list_nodes)
        btn_sel_all = QPushButton("Select All")
        btn_sel_all.clicked.connect(self.onSelectAll)
        node_layout.addWidget(btn_sel_all)
        splitter.addWidget(node_widget)
        splitter.setStretchFactor(0, 1)

        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.cmake_option_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.chk_cmake_opts = QCheckBox("Modify CMake Options")
        btn_row.addWidget(self.chk_cmake_opts)
        self.btn_add_cmake_opt = QPushButton("Add CMake Option")
        self.btn_add_cmake_opt.clicked.connect(self.onAddCMakeOptionField)
        btn_row.addWidget(self.btn_add_cmake_opt)
        self.cmake_option_layout.addLayout(btn_row)

        option_container = QWidget()
        option_container.setLayout(self.cmake_option_layout)
        option_scroll = QScrollArea()
        option_scroll.setWidgetResizable(True)
        option_scroll.setWidget(option_container)
        details_layout.addWidget(option_scroll)

        form_build = QFormLayout()

        # Build Directory
        self.chk_build_dir = QCheckBox()
        self.edit_build_dir = QLineEdit(os.path.join(os.getcwd(), "build"))
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_build_dir)
        h.addWidget(self.edit_build_dir)
        form_build.addRow("Build Directory:", w)

        # Build Type
        self.chk_build_type = QCheckBox()
        self.combo_build_type = QComboBox()
        self.combo_build_type.addItems(["Debug", "Release", "RelWithDebInfo", "MinSizeRel"])
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_build_type)
        h.addWidget(self.combo_build_type)
        form_build.addRow("Build Type:", w)

        # Install Directory
        self.chk_install_dir = QCheckBox()
        self.edit_install_dir = QLineEdit(os.path.join(os.getcwd(), "install"))
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_install_dir)
        h.addWidget(self.edit_install_dir)
        form_build.addRow("Install Directory:", w)

        # PREFIX_PATH
        self.chk_prefix_path = QCheckBox()
        self.edit_prefix_path = QLineEdit(os.path.join(os.getcwd(), "install"))
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_prefix_path)
        h.addWidget(self.edit_prefix_path)
        form_build.addRow("PREFIX_PATH:", w)

        # Toolchain file
        self.chk_toolchain = QCheckBox()
        self.edit_toolchain = QLineEdit()
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_toolchain)
        h.addWidget(self.edit_toolchain)
        form_build.addRow("Toolchain File:", w)

        # Generator
        self.chk_generator = QCheckBox()
        self.combo_generator = QComboBox()
        self.combo_generator.addItem("Default (not specified)")
        self.combo_generator.addItems([
            "Visual Studio 17 2022", "Visual Studio 16 2019",
            "Ninja", "Unix Makefiles",
        ])
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_generator)
        h.addWidget(self.combo_generator)
        form_build.addRow("CMake Generator:", w)

        # C compiler
        self.chk_c_compiler = QCheckBox()
        self.edit_c_compiler = QLineEdit()
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_c_compiler)
        h.addWidget(self.edit_c_compiler)
        form_build.addRow("C Compiler:", w)

        # C++ compiler
        self.chk_cxx_compiler = QCheckBox()
        self.edit_cxx_compiler = QLineEdit()
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.chk_cxx_compiler)
        h.addWidget(self.edit_cxx_compiler)
        form_build.addRow("C++ Compiler:", w)

        details_layout.addLayout(form_build)

        self.chk_py_before = QCheckBox()
        lbl_before = QLabel("Pre-Build Script (py_code_before_build):")
        h = QHBoxLayout()
        h.addWidget(self.chk_py_before)
        h.addWidget(lbl_before)
        h.addStretch()
        details_layout.addLayout(h)
        self.edit_py_before = QPlainTextEdit()
        details_layout.addWidget(self.edit_py_before)

        self.chk_py_after = QCheckBox()
        lbl_after = QLabel("Post-Install Script (py_code_after_install):")
        h = QHBoxLayout()
        h.addWidget(self.chk_py_after)
        h.addWidget(lbl_after)
        h.addStretch()
        details_layout.addLayout(h)
        self.edit_py_after = QPlainTextEdit()
        details_layout.addWidget(self.edit_py_after)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        details_layout.addWidget(buttons)

        splitter.addWidget(details_widget)
        splitter.setStretchFactor(1, 3)

    # ------------------------------------------------------------------
    def onSelectAll(self):
        for i in range(self.list_nodes.count()):
            item = self.list_nodes.item(i)
            item.setCheckState(Qt.CheckState.Checked)

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

    def loadFromNode(self, node: NodeItem):
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
    def applyToNodes(self) -> bool:
        selected = []
        for i in range(self.list_nodes.count()):
            item = self.list_nodes.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                nd = item.data(Qt.ItemDataRole.UserRole)
                if nd:
                    selected.append(nd)
        if not selected:
            QMessageBox.warning(self, "Warning", "No nodes selected.")
            return False

        new_opts = []
        if self.chk_cmake_opts.isChecked():
            for (_, line_edit) in self.cmake_option_rows:
                val = line_edit.text().strip()
                if val:
                    new_opts.append(val)

        for node in selected:
            # Update CMake options
            if self.chk_cmake_opts.isChecked() and new_opts:
                node.setCMakeOptions(node.cmakeOptions() + new_opts)

            bs = node.buildSettings()
            # Build directory
            if self.chk_build_dir.isChecked():
                bs.build_dir = self.edit_build_dir.text().strip()
            # Install directory
            if self.chk_install_dir.isChecked():
                bs.install_dir = self.edit_install_dir.text().strip()
            # Build type
            if self.chk_build_type.isChecked():
                bs.build_type = self.combo_build_type.currentText()
            # PREFIX_PATH
            if self.chk_prefix_path.isChecked():
                bs.prefix_path = self.edit_prefix_path.text().strip()
            # Toolchain
            if self.chk_toolchain.isChecked():
                bs.toolchain_file = self.edit_toolchain.text().strip()
            # Generator
            if self.chk_generator.isChecked():
                bs.generator = "" if self.combo_generator.currentIndex() == 0 else self.combo_generator.currentText()
            # C compiler
            if self.chk_c_compiler.isChecked():
                bs.c_compiler = self.edit_c_compiler.text().strip()
            # C++ compiler
            if self.chk_cxx_compiler.isChecked():
                bs.cxx_compiler = self.edit_cxx_compiler.text().strip()
            node.setBuildSettings(bs)

            if self.chk_py_before.isChecked():
                node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
            if self.chk_py_after.isChecked():
                node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True

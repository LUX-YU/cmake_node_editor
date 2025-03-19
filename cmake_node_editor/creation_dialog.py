# creation_dialog.py

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QWidget, QFileDialog, QMessageBox, QDialogButtonBox
)

class NodeCreationDialog(QDialog):
    """
    让用户输入节点名称，动态添加多个 CMake 选项，然后点击OK或Cancel。
    同时需要选择目标项目的文件夹，并检查是否存在 CMakeLists.txt。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建节点")

        # 存放各项输入
        self.node_name_edit = QLineEdit()
        self.node_options_layout = QVBoxLayout()
        self.option_edits = []

        # 项目路径
        self.project_path_edit = QLineEdit()
        self.btn_browse_project = QPushButton("选择文件夹")
        self.btn_browse_project.clicked.connect(self.onBrowseProject)

        # 初始添加一个空选项
        self.addOptionEdit()

        # “添加选项”按钮
        self.btn_add_option = QPushButton("添加选项")
        self.btn_add_option.clicked.connect(self.addOptionEdit)

        # 布局
        form = QFormLayout()
        form.addRow("节点名称：", self.node_name_edit)

        # 路径选择行
        proj_path_layout = QHBoxLayout()
        proj_path_layout.addWidget(self.project_path_edit)
        proj_path_layout.addWidget(self.btn_browse_project)
        form.addRow("目标项目路径：", proj_path_layout)

        opts_widget = QWidget()
        opts_layout = QVBoxLayout(opts_widget)
        opts_layout.addLayout(self.node_options_layout)
        opts_layout.addWidget(self.btn_add_option)
        form.addRow("CMake 选项：", opts_widget)

        # 对话框按钮 (OK / Cancel)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        self.buttons.accepted.connect(self.onAccept)
        self.buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addWidget(self.buttons)
        self.setLayout(main_layout)
        self.resize(500, 350)

    def addOptionEdit(self, text_value=""):
        edit = QLineEdit(text_value)
        self.node_options_layout.addWidget(edit)
        self.option_edits.append(edit)

    def onBrowseProject(self):
        folder = QFileDialog.getExistingDirectory(self, "选择项目文件夹", ".")
        if folder:
            self.project_path_edit.setText(folder)

    def onAccept(self):
        proj_path = self.project_path_edit.text().strip()
        if not os.path.isdir(proj_path):
            QMessageBox.critical(self, "错误", "请选择有效的项目文件夹。")
            return

        cmakelists_file = os.path.join(proj_path, "CMakeLists.txt")
        if not os.path.exists(cmakelists_file):
            QMessageBox.critical(self, "错误", "该文件夹下未找到 CMakeLists.txt！")
            return

        self.accept()

    def getNodeData(self):
        node_name = self.node_name_edit.text().strip()
        cmake_opts = []
        for ed in self.option_edits:
            val = ed.text().strip()
            if val:
                cmake_opts.append(val)
        proj_path = self.project_path_edit.text().strip()
        return node_name, cmake_opts, proj_path

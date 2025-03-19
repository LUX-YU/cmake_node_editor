import os
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox,
    QFileDialog, QGraphicsView
)

from .node_scene import NodeScene, NodeItem
from .creation_dialog import NodeCreationDialog


class NodeEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Blueprint-Style Node Editor - 同时保存/读取全局配置")
        self.resize(1600, 900)

        # 场景 & 视图
        self.scene = NodeScene(self)
        self.scene.setTopologyCallback(self.updateTopologyView)

        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setCentralWidget(self.view)

        # 构建输出 Dock
        self.dock_build_output = QDockWidget("构建输出", self)
        self.build_output_text = QPlainTextEdit()
        self.build_output_text.setReadOnly(True)
        self.dock_build_output.setWidget(self.build_output_text)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_build_output)

        # 右侧节点属性 Dock
        self.dock_properties = QDockWidget("节点属性", self)
        self.properties_widget = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_widget)
        self.dock_properties.setWidget(self.properties_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_properties)

        # 下方全局构建设置 Dock
        self.dock_build = QDockWidget("全局构建设置", self)
        self.build_widget = QWidget()
        self.build_layout = QFormLayout(self.build_widget)
        self.dock_build.setWidget(self.build_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_build)

        # 左侧拓扑排序 Dock
        self.dock_topology = QDockWidget("拓扑顺序", self)
        self.topology_view = QPlainTextEdit()
        self.topology_view.setReadOnly(True)
        self.dock_topology.setWidget(self.topology_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_topology)

        self.initGlobalBuildUI()
        self.initNodePropertiesUI()
        self.initMenu()

        self.current_node = None
        self.scene.selectionChanged.connect(self.onSceneSelectionChanged)

        self.updateTopologyView()

        # 用于异步执行命令的 QProcess 及队列
        self.process = None
        self.commands_queue = []
        self.current_cmd_index = 0

    # --------------------- 初始化菜单 ---------------------
    def initMenu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")

        act_save = file_menu.addAction("保存工程...")
        act_save.triggered.connect(self.onSaveProject)

        act_load = file_menu.addAction("读取工程...")
        act_load.triggered.connect(self.onLoadProject)

    def onSaveProject(self):
        """
        收集本窗口的“全局构建配置”后，调用 scene.saveProjectToJson(filepath, global_config)。
        """
        filepath, _ = QFileDialog.getSaveFileName(self, "保存工程", ".", "JSON Files (*.json)")
        if not filepath:
            return

        # 1. 收集全局设置
        global_cfg = {
            "build_dir": self.edit_build_dir.text().strip(),
            "install_dir": self.edit_install_dir.text().strip(),
            "build_type": self.combo_build_type.currentText(),
            "prefix_path": self.edit_prefix_path.text().strip(),
            "toolchain": self.edit_toolchain.text().strip(),
            "generator": self.combo_generator.currentText(),
            "start_node_id": self.edit_start_node_id.text().strip(),
        }

        # 2. 调用 scene.saveProjectToJson() 并传入 global_cfg
        self.scene.saveProjectToJson(filepath, global_cfg)
        QMessageBox.information(self, "提示", "工程已保存！")

    def onLoadProject(self):
        """
        调用 scene.loadProjectFromJson()，获得 global_cfg 并恢复到UI上。
        """
        filepath, _ = QFileDialog.getOpenFileName(self, "读取工程", ".", "JSON Files (*.json)")
        if not filepath:
            return

        global_cfg = self.scene.loadProjectFromJson(filepath)
        # global_cfg 若为空则返回 {}
        # 恢复到UI
        self.restoreGlobalConfig(global_cfg)
        QMessageBox.information(self, "提示", "工程已读取！")
        self.updateTopologyView()

    def restoreGlobalConfig(self, global_cfg):
        """
        将 global_cfg 填充到UI的全局构建设置中。
        """
        self.edit_build_dir.setText(global_cfg.get("build_dir", os.path.join(os.getcwd(), "build")))
        self.edit_install_dir.setText(global_cfg.get("install_dir", os.path.join(os.getcwd(), "install")))
        # 构建类型
        build_type = global_cfg.get("build_type", "Debug")
        idx = self.combo_build_type.findText(build_type)
        if idx >= 0:
            self.combo_build_type.setCurrentIndex(idx)
        else:
            self.combo_build_type.setCurrentText(build_type)  # 若找不到就直接设置文本

        self.edit_prefix_path.setText(global_cfg.get("prefix_path", os.path.join(os.getcwd(), "install")))
        self.edit_toolchain.setText(global_cfg.get("toolchain", ""))

        # 生成器
        gen = global_cfg.get("generator", "默认 (不指定)")
        idx_gen = self.combo_generator.findText(gen)
        if idx_gen >= 0:
            self.combo_generator.setCurrentIndex(idx_gen)
        else:
            self.combo_generator.setCurrentText(gen)

        # 起始节点ID
        self.edit_start_node_id.setText(global_cfg.get("start_node_id", ""))

    # --------------------- 全局构建设置 ---------------------
    def initGlobalBuildUI(self):
        self.edit_build_dir = QLineEdit(os.path.join(os.getcwd(), "build"))
        self.build_layout.addRow("构建目录：", self.edit_build_dir)

        self.combo_build_type = QComboBox()
        self.combo_build_type.addItems(["Debug", "Release", "RelWithDebInfo", "MinSizeRel"])
        self.build_layout.addRow("构建类型：", self.combo_build_type)

        self.edit_install_dir = QLineEdit(os.path.join(os.getcwd(), "install"))
        self.build_layout.addRow("安装目录：", self.edit_install_dir)

        self.edit_prefix_path = QLineEdit(os.path.join(os.getcwd(), "install"))
        self.build_layout.addRow("PREFIX_PATH：", self.edit_prefix_path)

        self.edit_toolchain = QLineEdit()
        self.build_layout.addRow("外部工具链路径：", self.edit_toolchain)

        self.combo_generator = QComboBox()
        self.combo_generator.addItem("默认 (不指定)")
        self.combo_generator.addItems([
            "Visual Studio 17 2022",
            "Visual Studio 16 2019",
            "Visual Studio 15 2017",
            "Visual Studio 14 2015",
            "Visual Studio 12 2013",
            "Visual Studio 9 2008",
            "Borland Makefiles",
            "NMake Makefiles",
            "NMake Makefiles JOM",
            "MSYS Makefiles",
            "MinGW Makefiles",
            "Unix Makefiles",
            "Ninja",
            "Ninja Multi-Config",
            "Watcom WMake",
            "CodeBlocks - MinGW Makefiles",
            "CodeBlocks - NMake Makefiles",
            "CodeBlocks - NMake Makefiles JOM",
            "CodeBlocks - Ninja",
            "CodeBlocks - Unix Makefiles",
            "CodeLite - MinGW Makefiles",
            "CodeLite - NMake Makefiles",
            "CodeLite - Ninja",
            "CodeLite - Unix Makefiles",
            "Eclipse CDT4 - NMake Makefiles",
            "Eclipse CDT4 - MinGW Makefiles",
            "Eclipse CDT4 - Ninja",
            "Eclipse CDT4 - Unix Makefiles",
            "Kate - MinGW Makefiles",
            "Kate - NMake Makefiles",
            "Kate - Ninja",
            "Kate - Unix Makefiles",
            "Sublime Text 2 - MinGW Makefiles",
            "Sublime Text 2 - NMake Makefiles",
            "Sublime Text 2 - Ninja",
            "Sublime Text 2 - Unix Makefiles"
        ])
        self.build_layout.addRow("CMake 生成器：", self.combo_generator)

        self.edit_start_node_id = QLineEdit()
        self.build_layout.addRow("起始节点ID：", self.edit_start_node_id)

        self.btn_build_all = QPushButton("开始构建并安装")
        self.btn_build_all.clicked.connect(self.onBuildAll)
        self.build_layout.addWidget(self.btn_build_all)

    # --------------------- 节点属性面板 ---------------------
    def initNodePropertiesUI(self):
        self.btn_new_node = QPushButton("新建节点")
        self.btn_new_node.clicked.connect(self.onAddNodeDialog)
        self.properties_layout.addWidget(self.btn_new_node)

        self.btn_delete_node = QPushButton("删除节点")
        self.btn_delete_node.clicked.connect(self.onDeleteNode)
        self.properties_layout.addWidget(self.btn_delete_node)

        self.properties_layout.addWidget(QLabel("----- 节点属性 -----"))

        form_for_name = QFormLayout()
        self.edit_node_name = QLineEdit()
        form_for_name.addRow("名称：", self.edit_node_name)
        self.properties_layout.addLayout(form_for_name)

        form_for_project_path = QFormLayout()
        self.edit_node_project_path = QLineEdit()
        form_for_project_path.addRow("项目路径：", self.edit_node_project_path)
        self.properties_layout.addLayout(form_for_project_path)

        # 放置若干CMake选项行
        self.cmake_option_layout = QVBoxLayout()
        self.cmake_option_rows = []
        btn_row = QHBoxLayout()
        self.btn_add_cmake_opt = QPushButton("添加选项")
        self.btn_add_cmake_opt.clicked.connect(self.onAddCMakeOptionField)
        btn_row.addWidget(self.btn_add_cmake_opt)
        self.cmake_option_layout.addLayout(btn_row)

        self.properties_layout.addLayout(self.cmake_option_layout)

        self.btn_apply_properties = QPushButton("应用到节点")
        self.btn_apply_properties.clicked.connect(self.onApplyNodeProperties)
        self.properties_layout.addWidget(self.btn_apply_properties)

        self.properties_layout.addStretch()

    def createOptionRow(self, text_value=""):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(text_value)
        btn_delete = QPushButton("删除")
        row_layout.addWidget(line_edit)
        row_layout.addWidget(btn_delete)

        btn_delete.clicked.connect(lambda: self.removeOptionRow(row_widget))

        return (row_widget, line_edit)

    def removeOptionRow(self, row_widget):
        found_index = None
        for i, (rw, le) in enumerate(self.cmake_option_rows):
            if rw == row_widget:
                found_index = i
                break
        if found_index is not None:
            row = self.cmake_option_rows[found_index]
            self.cmake_option_layout.removeWidget(row[0])
            row[0].deleteLater()
            self.cmake_option_rows.pop(found_index)

    def onAddCMakeOptionField(self):
        row_widget, line_edit = self.createOptionRow("")
        self.cmake_option_rows.append((row_widget, line_edit))
        self.cmake_option_layout.insertWidget(len(self.cmake_option_rows)-1, row_widget)

    # ------------------ 节点操作 ------------------
    def onAddNodeDialog(self):
        dlg = NodeCreationDialog(self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            node_name, opts, proj_path = dlg.getNodeData()
            if not node_name:
                node_name = f"Node_{self.scene.nodeCounter}"
            node = self.scene.addNewNode(node_name, opts, proj_path)
            self.scene.clearSelection()
            node.setSelected(True)

    def onDeleteNode(self):
        if self.current_node:
            self.scene.removeNode(self.current_node)
            self.current_node = None
            self.clearPropertiesPanel()

    def onSceneSelectionChanged(self):
        sel_items = self.scene.selectedItems()
        if sel_items and isinstance(sel_items[0], NodeItem):
            self.current_node = sel_items[0]
            self.updatePropertiesPanelFromNode()
        else:
            self.current_node = None
            self.clearPropertiesPanel()

    def clearPropertiesPanel(self):
        self.edit_node_name.clear()
        self.edit_node_project_path.clear()
        for (rw, le) in self.cmake_option_rows:
            self.cmake_option_layout.removeWidget(rw)
            rw.deleteLater()
        self.cmake_option_rows = []

    def updatePropertiesPanelFromNode(self):
        if not self.current_node:
            self.clearPropertiesPanel()
            return
        self.clearPropertiesPanel()
        self.edit_node_name.setText(self.current_node.title)
        self.edit_node_project_path.setText(self.current_node.project_path)

        for opt in self.current_node.cmake_option_list:
            row_widget, line_edit = self.createOptionRow(opt)
            self.cmake_option_rows.append((row_widget, line_edit))
            self.cmake_option_layout.insertWidget(len(self.cmake_option_rows)-1, row_widget)

    def onApplyNodeProperties(self):
        if not self.current_node:
            return
        new_title = self.edit_node_name.text().strip()
        if not new_title:
            new_title = f"Node_{self.current_node.node_id}"
        self.current_node.updateTitle(new_title)

        new_opts = []
        for (rw, le) in self.cmake_option_rows:
            val = le.text().strip()
            if val:
                new_opts.append(val)
        self.current_node.setCMakeOptions(new_opts)

        new_proj_path = self.edit_node_project_path.text().strip()
        self.current_node.setProjectPath(new_proj_path)

    # --------------------- 拓扑排序显示 ---------------------
    def updateTopologyView(self):
        sorted_nodes = self.scene.topologicalSort()
        if sorted_nodes is None:
            self.topology_view.setPlainText("检测到循环依赖，无法拓扑排序。")
        else:
            lines = []
            for i, node in enumerate(sorted_nodes):
                lines.append(f"{i+1}. {node.title} (ID={node.node_id})")
            self.topology_view.setPlainText("\n".join(lines))

    # --------------------- 异步构建流程 ---------------------
    def onBuildAll(self):
        """开始异步构建流程。"""
        build_root = self.edit_build_dir.text().strip()
        install_root = self.edit_install_dir.text().strip()
        build_type = self.combo_build_type.currentText()
        toolchain_path = self.edit_toolchain.text().strip()
        prefix_path = self.edit_prefix_path.text().strip()

        # 读取 Generator
        generator = self.combo_generator.currentText()
        if generator.startswith("默认"):
            generator = ""

        sorted_nodes = self.scene.topologicalSort()
        if sorted_nodes is None:
            QMessageBox.critical(self, "错误", "检测到循环依赖，无法进行构建！")
            return

        start_node_id_str = self.edit_start_node_id.text().strip()
        start_index = 0
        if start_node_id_str:
            try:
                start_id = int(start_node_id_str)
                found = None
                for i, node in enumerate(sorted_nodes):
                    if node.node_id == start_id:
                        found = i
                        break
                if found is not None:
                    start_index = found
                else:
                    QMessageBox.warning(self, "提示", f"未找到 ID={start_id} 的节点，将从头开始构建。")
            except ValueError:
                QMessageBox.warning(self, "提示", f"起始节点ID '{start_node_id_str}' 无效，将从头开始构建。")

        self.build_output_text.clear()
        self.commands_queue = []

        for node in sorted_nodes[start_index:]:
            project_name = node.title
            project_dir = node.project_path

            if not project_dir or not os.path.isdir(project_dir):
                QMessageBox.critical(self, "错误", f"{node.title} 未指定有效项目路径！")
                return
            cmakelists_file = os.path.join(project_dir, "CMakeLists.txt")
            if not os.path.exists(cmakelists_file):
                QMessageBox.critical(self, "错误", f"{node.title} 的项目路径下没有 CMakeLists.txt！")
                return

            node_build_dir = os.path.join(build_root, project_name, build_type)
            node_install_dir = os.path.join(install_root, build_type)
            if not os.path.exists(node_build_dir):
                os.makedirs(node_build_dir)

            # 配置命令
            cmd_config = [
                "cmake",
                "-S", project_dir,
                "-B", node_build_dir,
                f"-DCMAKE_BUILD_TYPE={build_type}",
                f"-DCMAKE_INSTALL_PREFIX={node_install_dir}"
            ]
            if generator:
                cmd_config.insert(1, f"-G{generator}")

            if toolchain_path:
                cmd_config.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_path}")
            if prefix_path:
                cmd_config.append(f"-DCMAKE_PREFIX_PATH={prefix_path}")
            for opt in node.cmake_option_list:
                cmd_config.append(opt)
            self.commands_queue.append((cmd_config, f"配置 {project_name}"))

            # 编译
            cmd_build = ["cmake", "--build", node_build_dir, "--config", build_type]
            self.commands_queue.append((cmd_build, f"编译 {project_name}"))

            # 安装
            cmd_install = ["cmake", "--install", node_build_dir, "--config", build_type]
            self.commands_queue.append((cmd_install, f"安装 {project_name}"))

        if not self.commands_queue:
            QMessageBox.information(self, "提示", "没有任何要构建的命令。")
            return

        self.btn_build_all.setEnabled(False)
        self.current_cmd_index = 0
        self.runNextCommand()

    def runNextCommand(self):
        if self.current_cmd_index >= len(self.commands_queue):
            QMessageBox.information(self, "完成", "所有项目已成功构建并安装！")
            self.btn_build_all.setEnabled(True)
            self.process = None
            return

        cmdList, displayName = self.commands_queue[self.current_cmd_index]
        self.build_output_text.appendPlainText(f"\n>>> 正在执行: {displayName}\n{' '.join(cmdList)}\n")

        if self.process:
            try:
                self.process.readyReadStandardOutput.disconnect()
                self.process.finished.disconnect()
            except:
                pass

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.onProcessOutputReady)
        self.process.finished.connect(self.onProcessFinished)

        program = cmdList[0]
        args = cmdList[1:]
        self.process.start(program, args)

    def onProcessOutputReady(self):
        if self.process:
            raw_data = self.process.readAllStandardOutput()
            text = bytes(raw_data).decode("utf-8", errors="replace")
            lines = text.splitlines()
            for line in lines:
                line_stripped = line.rstrip("\r")
                if line_stripped.strip():
                    self.build_output_text.appendPlainText(line_stripped)

    def onProcessFinished(self, exitCode, exitStatus):
        if exitStatus == QProcess.ExitStatus.CrashExit or exitCode != 0:
            self.build_output_text.appendPlainText(f"\n命令执行失败，exitCode={exitCode}.\n")
            QMessageBox.critical(self, "错误", f"命令执行失败，退出码={exitCode}")
            self.btn_build_all.setEnabled(True)
            self.process = None
            return

        self.current_cmd_index += 1
        self.runNextCommand()

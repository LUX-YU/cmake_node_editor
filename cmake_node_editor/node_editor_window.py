import os
import multiprocessing
from multiprocessing import Queue

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox,
    QFileDialog, QGraphicsView, QScrollArea, QProgressBar, QInputDialog, QMenu
)

from .node_scene import NodeScene, NodeItem
from .datas import (
    ProjectCommands, NodeCommands, CommandData,
    BuildSettings, SubprocessLogData, SubprocessResponseData
)
from .creation_dialog import NodeCreationDialog
from .worker import worker_main

class ResultListenerThread(QThread):
    """
    A background thread that continuously reads data from 'result_queue'.
    The data could be SubprocessLogData or SubprocessResponseData, etc.
    Then it emits signals to the main thread.
    """
    newLog      = pyqtSignal(SubprocessLogData)
    newResponse = pyqtSignal(SubprocessResponseData)

    def __init__(self, result_queue: Queue, parent=None):
        super().__init__(parent)
        self.result_queue = result_queue
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self.result_queue.get(timeout=1.0)
            except:
                continue

            if isinstance(data, SubprocessLogData):
                self.newLog.emit(data)
            elif isinstance(data, SubprocessResponseData):
                self.newResponse.emit(data)
            else:
                # Unknown data type, ignoring
                pass

    def stop(self):
        """
        Stop the background loop.
        """
        self._running = False


class NodeView(QGraphicsView):
    """QGraphicsView used for the node scene."""

    nodeCreateRequested = pyqtSignal()

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._panning = False
        self._last_mouse_pos = None
        self._press_pos = None
        
    def wheelEvent(self, event: QWheelEvent):
        scaleFactor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(scaleFactor, scaleFactor)
        else:
            self.scale(1.0 / scaleFactor, 1.0 / scaleFactor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._press_pos = event.pos()
            self._last_mouse_pos = event.pos()
            self._press_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super(NodeView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            moved = (event.pos() - self._press_pos).manhattanLength() if self._press_pos else 0
            self._panning = False
            if (event.pos() - self._press_pos).manhattanLength() < 5:
                from PyQt6.QtWidgets import QMenu
                menu = QMenu(self)
                act_create = menu.addAction("Create Node")
                chosen = menu.exec(event.globalPosition().toPoint())
                if chosen == act_create:
                    self.nodeCreateRequested.emit()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._press_pos = None
            if moved < 4:
                menu = QMenu(self)
                act_create = menu.addAction("Create Node")
                chosen = menu.exec(event.globalPosition().toPoint())
                if chosen == act_create:
                    win = self.window()
                    if hasattr(win, "onAddNodeDialog"):
                        win.onAddNodeDialog()
        else:
            super().mouseReleaseEvent(event)

    def showContextMenu(self, pos):
        menu = QMenu(self)
        act_new = menu.addAction("Create Node")
        action = menu.exec(self.mapToGlobal(pos))
        if action == act_new:
            main = self.window()
            if hasattr(main, "onAddNodeDialog"):
                main.onAddNodeDialog()

class NodeEditorWindow(QMainWindow):
    """
    The main window that holds:
      - A NodeScene (graphics) for node-based editing
      - Dock widgets for build logs, node properties, global build settings, topology.
      - A background subprocess for building commands, plus a ResultListenerThread for reading logs/responses.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QNode Editor for cmake projects")
        self.resize(1600, 900)

        # Create and configure NodeScene
        self.scene = NodeScene(self)
        self.scene.setTopologyCallback(self.updateTopologyView)

        # QGraphicsView for the scene
        self.view = NodeView(self.scene, self)
        self.setCentralWidget(self.view)
        self.view.nodeCreateRequested.connect(self.onAddNodeDialog)

        # Prepare dock widgets

        self.initBuildOutputDock()
        self.initBuildControlsDock()
        self.initPropertiesDock()

        self.initBuildControlsDock()
        self.initTopologyDock()
        self.initBuildControlDock()

        # Setup other UI pieces
        self.initNodePropertiesUI()
        self.initMenu()
        self.initStatusBar()

        # Connect scene signals
        self.current_node = None
        self.scene.selectionChanged.connect(self.onSceneSelectionChanged)

        self.updateTopologyView()

        # For multiprocessing
        self.task_queue = None
        self.result_queue = None
        self.worker_proc = None
        self.result_thread = None

        # Some placeholders
        self.commands_queue = []
        self.current_cmd_index = 0

    # ----------------------------------------------------------------
    # Dock widgets
    # ----------------------------------------------------------------
    def initBuildOutputDock(self):
        """
        Dock for displaying build logs.
        """
        self.dock_build_output = QDockWidget("Build Output", self)
        self.build_output_text = QPlainTextEdit()
        self.build_output_text.setReadOnly(True)
        self.dock_build_output.setWidget(self.build_output_text)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_build_output)

    def initBuildControlsDock(self):
        """Dock containing global build controls."""
        self.dock_build_controls = QDockWidget("Build Controls", self)
        widget = QWidget()
        layout = QFormLayout(widget)

        self.edit_start_node_id = QLineEdit()
        layout.addRow("Start Node ID:", self.edit_start_node_id)

        self.btn_build_all = QPushButton("Start Build")
        self.btn_build_all.clicked.connect(lambda: self.onBuildAll())
        layout.addWidget(self.btn_build_all)

        self.dock_build_controls.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_build_controls)

    def initPropertiesDock(self):
        """
        Dock for node properties.
        """
        self.dock_properties = QDockWidget("Node Properties", self)
        self.properties_widget = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_widget)

        self.properties_scroll = QScrollArea()
        self.properties_scroll.setWidgetResizable(True)
        self.properties_scroll.setWidget(self.properties_widget)

        self.dock_properties.setWidget(self.properties_scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_properties)
        self.dock_properties.hide()

    def initBuildControlsDock(self):
        """Dock with global build controls."""
        self.dock_build_controls = QDockWidget("Build Controls", self)
        widget = QWidget()
        layout = QFormLayout(widget)
        self.edit_start_node_id = QLineEdit()
        layout.addRow("Start Node ID:", self.edit_start_node_id)
        self.btn_build_all = QPushButton("Build Project")
        self.btn_build_all.clicked.connect(self.onBuildAll)
        layout.addWidget(self.btn_build_all)
        self.dock_build_controls.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_build_controls)


    def initTopologyDock(self):
        """
        Dock for topology order display.
        """
        self.dock_topology = QDockWidget("Topology Order", self)
        self.topology_view = QPlainTextEdit()
        self.topology_view.setReadOnly(True)
        self.dock_topology.setWidget(self.topology_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_topology)

    def initBuildControlDock(self):
        """
        Dock that holds global build controls like the start node ID and build button.
        """
        self.dock_build_ctrl = QDockWidget("Build Controls", self)
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        self.edit_start_node_id = QLineEdit()
        form.addRow("Start Node ID:", self.edit_start_node_id)
        layout.addLayout(form)

        self.btn_build_all = QPushButton("Start Build")
        self.btn_build_all.clicked.connect(lambda: self.onBuildAll())
        layout.addWidget(self.btn_build_all)

        layout.addStretch()
        self.dock_build_ctrl.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_build_ctrl)

    # ----------------------------------------------------------------
    # Window events
    # ----------------------------------------------------------------
    def closeEvent(self, event):
        # If there's a worker process running, stop it before closing
        self.stopWorkerProcess()
        super().closeEvent(event)

    # ----------------------------------------------------------------
    # Worker process handling
    # ----------------------------------------------------------------
    def stopWorkerProcess(self):
        """
        Stop the background worker process and the result listening thread, if any.
        """
        if self.result_thread:
            self.result_thread.stop()
            self.result_thread.wait(2000)
            self.result_thread = None

        if self.worker_proc and self.worker_proc.is_alive():
            self.task_queue.put("QUIT")
            self.worker_proc.join(timeout=2.0)
            if self.worker_proc.is_alive():
                self.worker_proc.terminate()

        self.worker_proc = None

    # ----------------------------------------------------------------
    # Menu
    # ----------------------------------------------------------------
    def initMenu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        act_save = file_menu.addAction("Save Project...")
        act_save.triggered.connect(self.onSaveProject)
        act_load = file_menu.addAction("Load Project...")
        act_load.triggered.connect(self.onLoadProject)

        project_menu = menubar.addMenu("Project")
        act_build_all = project_menu.addAction("Full Build")
        act_build_all.triggered.connect(self.onBuildAll)
        act_partial = project_menu.addAction("Partial Build")
        act_partial.triggered.connect(self.onPartialBuild)

        edit_menu = menubar.addMenu("Edit")
        act_create_node = edit_menu.addAction("Create Node")
        act_create_node.triggered.connect(self.onAddNodeDialog)

        windows_menu = menubar.addMenu("Windows")
        windows_menu.addAction(self.dock_build_output.toggleViewAction())
        windows_menu.addAction(self.dock_properties.toggleViewAction())
        windows_menu.addAction(self.dock_build_controls.toggleViewAction())
        windows_menu.addAction(self.dock_topology.toggleViewAction())

    def onSaveProject(self):
        """
        Gather global config, then call scene.saveProjectToJson(...)
        """
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project", ".", "JSON Files (*.json)")
        if not filepath:
            return

        global_cfg = {
            "start_node_id": self.edit_start_node_id.text().strip()
        }

        self.scene.saveProjectToJson(filepath, global_cfg.get("start_node_id"))
        QMessageBox.information(self, "Info", "Project has been saved!")

    def onLoadProject(self):
        """
        Load from JSON, restore config to UI
        """
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Project", ".", "JSON Files (*.json)")
        if not filepath:
            return

        global_cfg = self.scene.loadProjectFromJson(filepath)
        self.restoreGlobalConfig(global_cfg)
        QMessageBox.information(self, "Info", "Project loaded!")
        self.updateTopologyView()

    def restoreGlobalConfig(self, global_cfg):
        """
        Restore global build settings from the loaded dict.
        """
        self.edit_start_node_id.setText(global_cfg.get("start_node_id", ""))

    def onPartialBuild(self):
        if not self.scene.nodes:
            QMessageBox.information(self, "Info", "No nodes available.")
            return
        names = [n.title() for n in self.scene.nodes]
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(self, "Partial Build", "Start From:", names, 0, False)
        if not ok or not name:
            return
        for n in self.scene.nodes:
            if n.title() == name:
                self.edit_start_node_id.setText(str(n.id()))
                break
        self.onBuildAll()

    # ----------------------------------------------------------------
    # Node Properties UI
    # ----------------------------------------------------------------
    def initNodePropertiesUI(self):
        # Buttons for creating/deleting nodes
        self.btn_new_node = QPushButton("New Node")
        self.btn_new_node.clicked.connect(lambda: self.onAddNodeDialog())
        self.properties_layout.addWidget(self.btn_new_node)

        self.btn_delete_node = QPushButton("Delete Node")
        self.btn_delete_node.clicked.connect(lambda: self.onDeleteNode())
        self.properties_layout.addWidget(self.btn_delete_node)

        self.properties_layout.addWidget(QLabel("----- Node Properties -----"))

        form_for_name = QFormLayout()
        self.edit_node_name = QLineEdit()
        form_for_name.addRow("Name:", self.edit_node_name)
        self.properties_layout.addLayout(form_for_name)

        form_for_project_path = QFormLayout()
        self.edit_node_project_path = QLineEdit()
        form_for_project_path.addRow("Project Path:", self.edit_node_project_path)
        self.properties_layout.addLayout(form_for_project_path)

        # Layout for multiple CMake options
        self.cmake_option_layout = QVBoxLayout()
        self.cmake_option_rows = []
        btn_row = QHBoxLayout()
        self.btn_add_cmake_opt = QPushButton("Add CMake Option")
        self.btn_add_cmake_opt.clicked.connect(lambda: self.onAddCMakeOptionField())
        btn_row.addWidget(self.btn_add_cmake_opt)
        self.cmake_option_layout.addLayout(btn_row)

        option_container = QWidget()
        option_container.setLayout(self.cmake_option_layout)
        option_scroll = QScrollArea()
        option_scroll.setWidgetResizable(True)
        option_scroll.setWidget(option_container)

        self.properties_layout.addWidget(option_scroll)

        # Build settings
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

        self.properties_layout.addLayout(form_build)

        self.properties_layout.addWidget(QLabel("Pre-Build Script (py_code_before_build):"))
        self.edit_py_before = QPlainTextEdit()
        self.properties_layout.addWidget(self.edit_py_before)

        self.properties_layout.addWidget(QLabel("Post-Install Script (py_code_after_install):"))
        self.edit_py_after = QPlainTextEdit()
        self.properties_layout.addWidget(self.edit_py_after)

        self.btn_build_node = QPushButton("Build Node")
        self.btn_build_node.clicked.connect(self.onBuildNode)
        self.properties_layout.addWidget(self.btn_build_node)

        self.btn_apply_properties = QPushButton("Apply Node Properties")
        self.btn_apply_properties.clicked.connect(lambda: self.onApplyNodeProperties())
        self.properties_layout.addWidget(self.btn_apply_properties)

        self.properties_layout.addStretch()

    def createOptionRow(self, text_value=""):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(text_value)
        btn_delete = QPushButton("Delete")
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
        self.cmake_option_layout.insertWidget(self.cmake_option_layout.count() - 1, row_widget)

    # ----------------------------------------------------------------
    # Node operations
    # ----------------------------------------------------------------
    def onAddNodeDialog(self):
        dlg = NodeCreationDialog(self, existing_nodes=self.scene.nodes)
        if dlg.exec() == dlg.DialogCode.Accepted:
            node_name, opts, proj_path, inherit_idx, flags = dlg.getNodeData()
            if inherit_idx >= 0 and inherit_idx < len(self.scene.nodes):
                base_node = self.scene.nodes[inherit_idx]
            else:
                base_node = None
            if base_node:
                if flags.get("project"):
                    proj_path = base_node.projectPath()
                if flags.get("options"):
                    opts = list(base_node.cmakeOptions())
                if flags.get("build"):
                    bs = base_node.buildSettings()
                else:
                    bs = None
            else:
                bs = None

            if not node_name:
                node_name = f"Node_{self.scene.nodeCounter}"
            if any(n.title() == node_name for n in self.scene.nodes):
                QMessageBox.warning(self, "Warning", f"Node name '{node_name}' already exists.")
                return
            new_node = self.scene.addNewNode(node_name, opts, proj_path, bs)
            self.scene.clearSelection()
            new_node.setSelected(True)

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
            self.dock_properties.show()
        else:
            self.current_node = None
            self.clearPropertiesPanel()
            self.dock_properties.hide()

    def clearPropertiesPanel(self):
        self.edit_node_name.clear()
        self.edit_node_project_path.clear()
        for (row_w, line_edit) in self.cmake_option_rows:
            self.cmake_option_layout.removeWidget(row_w)
            row_w.deleteLater()
        self.cmake_option_rows = []
        self.edit_build_dir.clear()
        self.edit_install_dir.clear()
        self.edit_prefix_path.clear()
        self.edit_toolchain.clear()
        self.edit_c_compiler.clear()
        self.edit_cxx_compiler.clear()
        self.edit_py_before.clear()
        self.edit_py_after.clear()

    def updatePropertiesPanelFromNode(self):
        if not self.current_node:
            self.clearPropertiesPanel()
            return
        self.clearPropertiesPanel()

        self.edit_node_name.setText(self.current_node.title())
        self.edit_node_project_path.setText(self.current_node.projectPath())

        for opt in self.current_node.cmakeOptions():
            row_widget, line_edit = self.createOptionRow(opt)
            self.cmake_option_rows.append((row_widget, line_edit))
            self.cmake_option_layout.insertWidget(len(self.cmake_option_rows)-1, row_widget)

        bs = self.current_node.buildSettings()
        self.edit_build_dir.setText(bs.build_dir)
        idx_bt = self.combo_build_type.findText(bs.build_type)
        if idx_bt >= 0:
            self.combo_build_type.setCurrentIndex(idx_bt)
        else:
            self.combo_build_type.setCurrentText(bs.build_type)
        self.edit_install_dir.setText(bs.install_dir)
        self.edit_prefix_path.setText(bs.prefix_path)
        self.edit_toolchain.setText(bs.toolchain_file)
        gen_idx = self.combo_generator.findText(bs.generator)
        if gen_idx >= 0:
            self.combo_generator.setCurrentIndex(gen_idx)
        else:
            self.combo_generator.setCurrentText(bs.generator)
        self.edit_c_compiler.setText(bs.c_compiler)
        self.edit_cxx_compiler.setText(bs.cxx_compiler)

        self.edit_py_before.setPlainText(self.current_node.codeBeforeBuild())
        self.edit_py_after.setPlainText(self.current_node.codeAfterInstall())

    def onApplyNodeProperties(self):
        if not self.current_node:
            return

        new_title = self.edit_node_name.text().strip()
        if not new_title:
            new_title = f"Node_{self.current_node.id()}"
        elif any(n.title() == new_title and n != self.current_node for n in self.scene.nodes):
            QMessageBox.warning(self, "Warning", f"Node name '{new_title}' already exists.")
            return
        self.current_node.updateTitle(new_title)

        # Collect new CMake options
        new_opts = []
        for (row_w, line_edit) in self.cmake_option_rows:
            val = line_edit.text().strip()
            if val:
                new_opts.append(val)
        self.current_node.setCMakeOptions(new_opts)

        new_proj_path = self.edit_node_project_path.text().strip()
        self.current_node.setProjectPath(new_proj_path)

        bs = BuildSettings(
            build_dir=self.edit_build_dir.text().strip(),
            install_dir=self.edit_install_dir.text().strip(),
            build_type=self.combo_build_type.currentText(),
            prefix_path=self.edit_prefix_path.text().strip(),
            toolchain_file=self.edit_toolchain.text().strip(),
            generator=self.combo_generator.currentText(),
            c_compiler=self.edit_c_compiler.text().strip(),
            cxx_compiler=self.edit_cxx_compiler.text().strip(),
        )
        self.current_node.setBuildSettings(bs)

        self.current_node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
        self.current_node.setCodeAfterInstall(self.edit_py_after.toPlainText())

    # ----------------------------------------------------------------
    # Topology view
    # ----------------------------------------------------------------
    def updateTopologyView(self):
        sorted_nodes = self.scene.topologicalSort()
        if sorted_nodes is None:
            self.topology_view.setPlainText("Detected circular dependency, cannot build.")
        else:
            lines = []
            for i, node_item in enumerate(sorted_nodes):
                lines.append(f"{i+1}. {node_item.title()} (ID={node_item.id()})")
            self.topology_view.setPlainText("\n".join(lines))

    # ----------------------------------------------------------------
    # Asynchronous build flow
    # ----------------------------------------------------------------
    def onBuildAll(self, start_node_name=None, force_first=False):
        """
        Gather global build config, do a topological sort, build a ProjectCommands,
        start the worker process & result thread, then send the commands to the worker.
        """
        self.build_output_text.clear()

        # Topological sort
        sorted_nodes = self.scene.topologicalSort()
        if sorted_nodes is None:
            QMessageBox.critical(self, "Error", "Detected circular dependency, cannot build.")
            return

        start_id = None
        start_index = 0
        start_node_id_str = self.edit_start_node_id.text().strip()
        if start_node_id_str:
            try:
                sid = int(start_node_id_str)
                for idx, node_item in enumerate(sorted_nodes):
                    if node_item.id() == sid:
                        start_id = sid
                        start_index = idx
                        break
                if start_id is None:
                    QMessageBox.warning(self, "Warning", f"Node ID={sid} not found, building from beginning.")
            except ValueError:
                QMessageBox.warning(self, "Warning", f"Start Node ID '{start_node_id_str}' invalid, building from beginning.")

        project_commands = ProjectCommands(
            start_node_id=start_id if start_id is not None else -1,
            node_commands_list=[]
        )

        # For each node in sorted order, build NodeCommands & CommandData
        for node_obj in sorted_nodes[start_index:]:
            node_cmd = NodeCommands(index=node_obj.id(), node_data=node_obj.nodeData(), cmd_list=[])

            bs = node_obj.buildSettings()
            build_root = bs.build_dir
            install_root = bs.install_dir
            build_type = bs.build_type
            toolchain_path = bs.toolchain_file
            prefix_path = bs.prefix_path
            generator = bs.generator
            c_compiler = bs.c_compiler
            cxx_compiler = bs.cxx_compiler

            # Pre-build script
            if node_obj.codeBeforeBuild().strip():
                pre_script_cmd = CommandData(
                    type="script",
                    cmd=node_obj.codeBeforeBuild(),
                    display_name=f"Pre-Build Script {node_obj.title()}"
                )
                node_cmd.cmd_list.append(pre_script_cmd)

            # Checking project path, cmake commands, etc.
            project_name = node_obj.title()
            project_dir  = node_obj.projectPath()
            if not project_dir or not os.path.isdir(project_dir):
                QMessageBox.critical(self, "Error", f"{project_name} has invalid project path.")
                return

            cmake_lists_file = os.path.join(project_dir, "CMakeLists.txt")
            if not os.path.exists(cmake_lists_file):
                QMessageBox.critical(self, "Error", f"CMakeLists.txt not found in {project_dir}.")
                return

            node_build_dir = os.path.join(build_root, project_name, build_type)
            node_install_dir = os.path.join(install_root, build_type)
            os.makedirs(node_build_dir, exist_ok=True)

            # Example: "cmake -S ... -B ... -DCMAKE_BUILD_TYPE=... -DCMAKE_INSTALL_PREFIX=..."
            cmd_configure = [
                "cmake",
                "-S", project_dir,
                "-B", node_build_dir,
                f"-DCMAKE_BUILD_TYPE:STRING={build_type}",
                f"-DCMAKE_INSTALL_PREFIX={node_install_dir}"
            ]
            if generator:
                cmd_configure[1:1] = ["-G", generator]
            if c_compiler:
                cmd_configure.append(f"-DCMAKE_C_COMPILER:FILEPATH={c_compiler}")
            if cxx_compiler:
                cmd_configure.append(f"-DCMAKE_CXX_COMPILER:FILEPATH={cxx_compiler}")
            if toolchain_path:
                cmd_configure.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_path}")
            if prefix_path:
                cmd_configure.append(f"-DCMAKE_PREFIX_PATH={prefix_path}")
            for opt in node_obj.cmakeOptions():
                cmd_configure.append(opt)

            node_cmd.cmd_list.append(CommandData(
                type="cmd", cmd=cmd_configure, display_name=f"Configure {project_name}"
            ))

            # Build command
            cmd_build = [
                "cmake", "--build", node_build_dir,
                "--config", build_type,
                "--parallel", str(multiprocessing.cpu_count())
            ]
            node_cmd.cmd_list.append(CommandData(
                type="cmd", cmd=cmd_build, display_name=f"Build {project_name}"
            ))

            # Install command
            cmd_install = ["cmake", "--install", node_build_dir, "--config", build_type]
            node_cmd.cmd_list.append(CommandData(
                type="cmd", cmd=cmd_install, display_name=f"Install {project_name}"
            ))

            # Post-install script
            if node_obj.codeAfterInstall().strip():
                post_script_cmd = CommandData(
                    type="script",
                    cmd=node_obj.codeAfterInstall(),
                    display_name=f"Post-Install Script {project_name}"
                )
                node_cmd.cmd_list.append(post_script_cmd)

            project_commands.node_commands_list.append(node_cmd)

        if not project_commands.node_commands_list:
            QMessageBox.information(self, "Info", "No commands to build.")
            return

        # Disable build buttons while running
        self.btn_build_all.setEnabled(False)
        self.btn_build_node.setEnabled(False)

        # Create queues and start worker process
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.worker_proc = multiprocessing.Process(
            target=worker_main,
            args=(self.task_queue, self.result_queue)
        )
        self.worker_proc.start()

        # Start background thread to listen result_queue
        self.result_thread = ResultListenerThread(self.result_queue)
        self.result_thread.newLog.connect(self.onWorkerLog)
        self.result_thread.newResponse.connect(self.onWorkerResponse)
        self.result_thread.start()

        # Send project_commands to worker
        self.task_queue.put(project_commands)
        self.build_output_text.appendPlainText("[Main] Sent ProjectCommands to worker.")

    def onBuildNode(self):
        if not self.current_node:
            QMessageBox.information(self, "Info", "No node selected.")
            return
        self.build_output_text.clear()
        node_obj = self.current_node
        node_cmd = NodeCommands(index=node_obj.id(), node_data=node_obj.nodeData(), cmd_list=[])

        bs = node_obj.buildSettings()
        build_root = bs.build_dir
        install_root = bs.install_dir
        build_type = bs.build_type
        toolchain_path = bs.toolchain_file
        prefix_path = bs.prefix_path
        generator = bs.generator
        c_compiler = bs.c_compiler
        cxx_compiler = bs.cxx_compiler

        if node_obj.codeBeforeBuild().strip():
            node_cmd.cmd_list.append(CommandData(
                type="script",
                cmd=node_obj.codeBeforeBuild(),
                display_name=f"Pre-Build Script {node_obj.title()}"
            ))

        project_name = node_obj.title()
        project_dir = node_obj.projectPath()
        if not project_dir or not os.path.isdir(project_dir):
            QMessageBox.critical(self, "Error", f"{project_name} has invalid project path.")
            return
        cmake_lists_file = os.path.join(project_dir, "CMakeLists.txt")
        if not os.path.exists(cmake_lists_file):
            QMessageBox.critical(self, "Error", f"CMakeLists.txt not found in {project_dir}.")
            return

        node_build_dir = os.path.join(build_root, project_name, build_type)
        node_install_dir = os.path.join(install_root, build_type)
        os.makedirs(node_build_dir, exist_ok=True)

        cmd_configure = [
            "cmake",
            "-S", project_dir,
            "-B", node_build_dir,
            f"-DCMAKE_BUILD_TYPE:STRING={build_type}",
            f"-DCMAKE_INSTALL_PREFIX={node_install_dir}"
        ]
        if generator:
            cmd_configure[1:1] = ["-G", generator]
        if c_compiler:
            cmd_configure.append(f"-DCMAKE_C_COMPILER:FILEPATH={c_compiler}")
        if cxx_compiler:
            cmd_configure.append(f"-DCMAKE_CXX_COMPILER:FILEPATH={cxx_compiler}")
        if toolchain_path:
            cmd_configure.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_path}")
        if prefix_path:
            cmd_configure.append(f"-DCMAKE_PREFIX_PATH={prefix_path}")
        for opt in node_obj.cmakeOptions():
            cmd_configure.append(opt)

        node_cmd.cmd_list.append(CommandData(
            type="cmd", cmd=cmd_configure, display_name=f"Configure {project_name}"
        ))

        cmd_build = [
            "cmake", "--build", node_build_dir,
            "--config", build_type,
            "--parallel", str(multiprocessing.cpu_count())
        ]
        node_cmd.cmd_list.append(CommandData(
            type="cmd", cmd=cmd_build, display_name=f"Build {project_name}"
        ))

        cmd_install = ["cmake", "--install", node_build_dir, "--config", build_type]
        node_cmd.cmd_list.append(CommandData(
            type="cmd", cmd=cmd_install, display_name=f"Install {project_name}"
        ))

        if node_obj.codeAfterInstall().strip():
            node_cmd.cmd_list.append(CommandData(
                type="script",
                cmd=node_obj.codeAfterInstall(),
                display_name=f"Post-Install Script {project_name}"
            ))

        project_commands = ProjectCommands(start_node_id=node_obj.id(), node_commands_list=[node_cmd])

        self.btn_build_all.setEnabled(False)
        self.btn_build_node.setEnabled(False)

        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.worker_proc = multiprocessing.Process(
            target=worker_main,
            args=(self.task_queue, self.result_queue)
        )
        self.worker_proc.start()

        self.result_thread = ResultListenerThread(self.result_queue)
        self.result_thread.newLog.connect(self.onWorkerLog)
        self.result_thread.newResponse.connect(self.onWorkerResponse)
        self.result_thread.start()

        self.task_queue.put(project_commands)
        self.build_output_text.appendPlainText("[Main] Sent NodeCommands to worker.")

    def onWorkerLog(self, logData: SubprocessLogData):
        """
        Receive SubprocessLogData from child process, append to log output.
        """
        self.build_output_text.appendPlainText(logData.log)

    def onWorkerResponse(self, respData: SubprocessResponseData):
        """
        Receive SubprocessResponseData from child process, e.g. success/failure indication.
        If respData.index == -1 => entire build finished (success or fail).
        """
        result_str = "SUCCESS" if respData.result else "FAILED"
        self.build_output_text.appendPlainText(
            f"[Worker Response idx={respData.index}] Command {result_str}"
        )

        if respData.index >= 0:
            self.current_progress += 1
            self.progress_bar.setValue(self.current_progress)

        # If index == -1, means entire build ended.
        if respData.index == -1:
            if respData.result:
                self.build_output_text.appendPlainText("Build Completed!")
            else:
                self.build_output_text.appendPlainText("Build Failed!")

            # Stop worker process, re-enable build buttons
            self.stopWorkerProcess()
            self.btn_build_all.setEnabled(True)
            self.btn_build_node.setEnabled(True)

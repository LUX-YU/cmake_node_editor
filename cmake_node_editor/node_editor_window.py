import os
import multiprocessing
from multiprocessing import Queue

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox,
    QFileDialog, QGraphicsView, QScrollArea, QProgressBar, QInputDialog, QMenu
)

from .node_scene import NodeScene, NodeItem, Edge
from .datas import (
    ProjectCommands, NodeCommands, CommandData,
    BuildSettings, SubprocessLogData, SubprocessResponseData
)
from .creation_dialog import NodeCreationDialog
from .settings_dialog import SettingsDialog
from .node_properties_dialog import NodePropertiesDialog
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
    """A QGraphicsView that holds the NodeScene."""

    createNodeRequested = pyqtSignal()

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._panning = False
        self._last_mouse_pos = None
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        
    def wheelEvent(self, event: QWheelEvent):
        scaleFactor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(scaleFactor, scaleFactor)
        else:
            self.scale(1.0 / scaleFactor, 1.0 / scaleFactor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_mouse_pos = event.pos()
            self._press_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super(NodeView, self).mousePressEvent(event)

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
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._press_pos = None
            if moved < 4:
                self.openContextMenu(event.globalPosition().toPoint(), event.pos())
        else:
            super(NodeView, self).mouseReleaseEvent(event)

    def showContextMenu(self, pos):
        self.openContextMenu(self.mapToGlobal(pos), pos)

    def openContextMenu(self, global_pos, view_pos):
        scene_pos = self.mapToScene(view_pos)
        item = self.scene().itemAt(scene_pos, self.transform())
        menu = QMenu(self)
        if isinstance(item, NodeItem):
            act_prop = menu.addAction("Properties")
            action = menu.exec(global_pos)
            if action == act_prop:
                parent = self.parent()
                if parent and hasattr(parent, 'openNodePropertyDialog'):
                    parent.openNodePropertyDialog(item)
        else:
            act_new = menu.addAction("Create Node")
            action = menu.exec(global_pos)
            if action == act_new:
                self.createNodeRequested.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            scene = self.scene()
            for item in scene.selectedItems():
                if isinstance(item, Edge):
                    scene.removeEdge(item)
                elif isinstance(item, NodeItem):
                    scene.removeNode(item)
            event.accept()
        else:
            super().keyPressEvent(event)

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
        self.view.createNodeRequested.connect(self.onAddNodeDialog)
        self.setCentralWidget(self.view)

        # Prepare dock widgets

        self.initBuildOutputDock()
        self.initBuildControlsDock()
        self.initTopologyDock()

        # Setup other UI pieces
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
        """Create the dock widget used for global build controls."""
        self.dock_build_controls = QDockWidget("Build Controls", self)
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        self.edit_start_node_id = QLineEdit()
        form.addRow("Start Node ID:", self.edit_start_node_id)
        layout.addLayout(form)

        self.btn_build_all = QPushButton("Start Build")
        self.btn_build_all.clicked.connect(self.onBuildAll)
        layout.addWidget(self.btn_build_all)

        layout.addStretch()
        self.dock_build_controls.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_build_controls)


    def initTopologyDock(self):
        """
        Dock for topology order display.
        """
        self.dock_topology = QDockWidget("Topology Order", self)
        self.topology_view = QPlainTextEdit()
        self.topology_view.setReadOnly(True)
        self.dock_topology.setWidget(self.topology_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_topology)


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

        act_settings = file_menu.addAction("Settings")
        act_settings.triggered.connect(self.onSettings)

        project_menu = menubar.addMenu("Project")
        act_full = project_menu.addAction("Full Build")
        act_full.triggered.connect(lambda: self.onBuildAll(start_node_name=None, force_first=True))
        act_partial = project_menu.addAction("Partial Build")
        act_partial.triggered.connect(self.onPartialBuild)

        edit_menu = menubar.addMenu("Edit")
        self.act_add_node = edit_menu.addAction("Add Node")
        self.act_add_node.triggered.connect(self.onAddNodeDialog)
        self.act_edit_node = edit_menu.addAction("Edit Node")
        self.act_edit_node.triggered.connect(lambda: self.openNodePropertyDialog(self.current_node))
        self.act_edit_node.setEnabled(False)
        self.act_remove_node = edit_menu.addAction("Remove Node")
        self.act_remove_node.triggered.connect(self.onDeleteNode)
        self.act_remove_node.setEnabled(False)

        windows_menu = menubar.addMenu("Windows")

        self.act_win_build_ctrl = windows_menu.addAction("Build Controls")
        self.act_win_build_ctrl.setCheckable(True)
        self.act_win_build_ctrl.setChecked(True)
        self.act_win_build_ctrl.toggled.connect(self.dock_build_controls.setVisible)

        self.act_win_build_out = windows_menu.addAction("Build Output")
        self.act_win_build_out.setCheckable(True)
        self.act_win_build_out.setChecked(True)
        self.act_win_build_out.toggled.connect(self.dock_build_output.setVisible)

        self.act_win_topology = windows_menu.addAction("Topology Order")
        self.act_win_topology.setCheckable(True)
        self.act_win_topology.setChecked(True)
        self.act_win_topology.toggled.connect(self.dock_topology.setVisible)

    def initStatusBar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(1)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)

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

    def onSettings(self):
        current_style = QApplication.style().objectName()
        dlg = SettingsDialog(current_style, self.scene.gridOpacity(), self.scene.linkColor(), self)
        if dlg.exec():
            style_name, opacity, link_color = dlg.getValues()
            QApplication.setStyle(style_name)
            self.scene.setGridOpacity(opacity)
            self.scene.setLinkColor(link_color)

    def onPartialBuild(self):
        names = [n.title() for n in self.scene.nodes]
        if not names:
            QMessageBox.information(self, "Info", "No nodes available")
            return
        name, ok = QInputDialog.getItem(self, "Partial Build", "Start from node:", names, 0, False)
        if ok and name:
            self.onBuildAll(start_node_name=name)

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

    def onSceneSelectionChanged(self):
        sel_items = self.scene.selectedItems()
        if sel_items and isinstance(sel_items[0], NodeItem):
            self.current_node = sel_items[0]
            if hasattr(self, 'act_remove_node'):
                self.act_remove_node.setEnabled(True)
            if hasattr(self, 'act_edit_node'):
                self.act_edit_node.setEnabled(True)
        else:
            self.current_node = None
            if hasattr(self, 'act_remove_node'):
                self.act_remove_node.setEnabled(False)
            if hasattr(self, 'act_edit_node'):
                self.act_edit_node.setEnabled(False)

    def openNodePropertyDialog(self, node: NodeItem):
        if not node:
            return
        dlg = NodePropertiesDialog(node, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            dlg.applyToNode()

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
        if force_first:
            start_id = sorted_nodes[0].id() if sorted_nodes else -1
        elif start_node_name:
            for idx, node_item in enumerate(sorted_nodes):
                if node_item.title() == start_node_name:
                    start_id = node_item.id()
                    start_index = idx
                    break
            if start_id is None:
                QMessageBox.warning(self, "Warning", f"Node '{start_node_name}' not found, building from beginning.")
        else:
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

        # Disable build button and setup progress bar
        self.btn_build_all.setEnabled(False)
        self.total_steps = len(project_commands.node_commands_list)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.current_progress = 0

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

            # Stop worker process, re-enable build button
            self.stopWorkerProcess()
            self.btn_build_all.setEnabled(True)
            self.progress_bar.hide()

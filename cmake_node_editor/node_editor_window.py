import os
import multiprocessing
from multiprocessing import Queue

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QFormLayout, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox,
    QFileDialog, QGraphicsView, QScrollArea, QProgressBar, QMenu,
    QListWidget, QListWidgetItem, QSpinBox, QDialog, QDialogButtonBox
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
            act_cfg_node = menu.addAction("Configure Node")
            act_build_node = menu.addAction("Build Node")
            act_install_node = menu.addAction("Install Node")
            menu.addSeparator()
            act_cfg_from = menu.addAction("Configure From This")
            act_build_from = menu.addAction("Build From This")
            act_install_from = menu.addAction("Install From This")
            menu.addSeparator()
            act_open_dir = menu.addAction("Open Project Directory")
            menu.addSeparator()
            act_prop = menu.addAction("Properties")
            action = menu.exec(global_pos)
            parent = self.parent()
            if not parent:
                return
            if action == act_prop and hasattr(parent, 'openNodePropertyDialog'):
                parent.openNodePropertyDialog(item)
            elif action == act_open_dir:
                proj_dir = item.projectPath()
                if proj_dir and os.path.isdir(proj_dir):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(proj_dir)))
                else:
                    QMessageBox.warning(self, "Warning", "Invalid project directory")
            elif hasattr(parent, 'runStage'):
                if action == act_cfg_node:
                    parent.runStage(stage="configure", start_node_id=item.id(), only_first=True)
                elif action == act_build_node:
                    parent.runStage(stage="build", start_node_id=item.id(), only_first=True)
                elif action == act_install_node:
                    parent.runStage(stage="install", start_node_id=item.id(), only_first=True)
                elif action == act_cfg_from:
                    parent.runStage(stage="configure", start_node_id=item.id())
                elif action == act_build_from:
                    parent.runStage(stage="build", start_node_id=item.id())
                elif action == act_install_from:
                    parent.runStage(stage="install", start_node_id=item.id())
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


class NodeRangeDialog(QDialog):
    """Dialog to input a start and end node ID."""

    def __init__(self, min_id: int, max_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Node ID Range")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.start_spin = QSpinBox()
        self.start_spin.setRange(min_id, max_id)
        self.start_spin.setValue(min_id)
        self.end_spin = QSpinBox()
        self.end_spin.setRange(min_id, max_id)
        self.end_spin.setValue(max_id)
        form.addRow("Start ID:", self.start_spin)
        form.addRow("End ID:", self.end_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getValues(self) -> tuple[int, int]:
        return self.start_spin.value(), self.end_spin.value()

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


    def initTopologyDock(self):
        """
        Dock for topology order display.
        """
        self.dock_topology = QDockWidget("Node Inspector", self)
        self.topology_view = QListWidget()
        self.topology_view.itemClicked.connect(self.onInspectorItemClicked)
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
        act_full_cfg = project_menu.addAction("Full Configure")
        act_full_cfg.triggered.connect(lambda: self.runStage(stage="configure", force_first=True))
        act_full_build = project_menu.addAction("Full Build")
        act_full_build.triggered.connect(lambda: self.runStage(stage="build", force_first=True))
        act_full_install = project_menu.addAction("Full Install")
        act_full_install.triggered.connect(lambda: self.runStage(stage="install", force_first=True))
        project_menu.addSeparator()
        act_part_cfg = project_menu.addAction("Partial Configure")
        act_part_cfg.triggered.connect(lambda: self.onPartialStage("configure"))
        act_part_build = project_menu.addAction("Partial Build")
        act_part_build.triggered.connect(lambda: self.onPartialStage("build"))
        act_part_install = project_menu.addAction("Partial Install")
        act_part_install.triggered.connect(lambda: self.onPartialStage("install"))

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

        self.act_win_build_out = windows_menu.addAction("Build Output")
        self.act_win_build_out.setCheckable(True)
        self.act_win_build_out.setChecked(True)
        self.act_win_build_out.toggled.connect(self.dock_build_output.setVisible)

        self.act_win_topology = windows_menu.addAction("Node Inspector")
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

        self.scene.saveProjectToJson(filepath, None)
        QMessageBox.information(self, "Info", "Project has been saved!")

    def onLoadProject(self):
        """
        Load from JSON, restore config to UI
        """
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Project", ".", "JSON Files (*.json)")
        if not filepath:
            return

        self.scene.loadProjectFromJson(filepath)
        QMessageBox.information(self, "Info", "Project loaded!")
        self.updateTopologyView()

    def onSettings(self):
        current_style = QApplication.style().objectName()
        dlg = SettingsDialog(current_style, self.scene.gridOpacity(), self.scene.linkColor(), self)
        if dlg.exec():
            style_name, opacity, link_color = dlg.getValues()
            QApplication.setStyle(style_name)
            self.scene.setGridOpacity(opacity)
            self.scene.setLinkColor(link_color)

    def onPartialStage(self, stage: str) -> None:
        sorted_nodes = self.scene.topologicalSort()
        if not sorted_nodes:
            QMessageBox.information(self, "Info", "No nodes available")
            return
        dlg = NodeRangeDialog(sorted_nodes[0].id(), sorted_nodes[-1].id(), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            s_id, e_id = dlg.getValues()
            ids = [n.id() for n in sorted_nodes]
            if s_id not in ids:
                QMessageBox.warning(self, "Warning", f"Start ID {s_id} not found.")
                return
            if e_id not in ids:
                QMessageBox.warning(self, "Warning", f"End ID {e_id} not found.")
                return
            if ids.index(e_id) < ids.index(s_id):
                QMessageBox.warning(self, "Warning", "Invalid node range.")
                return
            self.runStage(stage=stage, start_node_id=s_id, end_node_id=e_id)

    # ----------------------------------------------------------------
    # Node operations
    # ----------------------------------------------------------------
    def onAddNodeDialog(self):
        dlg = NodeCreationDialog(self, existing_nodes=self.scene.nodes)
        if dlg.exec() == dlg.DialogCode.Accepted:
            node_name, opts, proj_path, inherit_idx, attrs = dlg.getNodeData()
            if inherit_idx >= 0 and inherit_idx < len(self.scene.nodes):
                base_node = self.scene.nodes[inherit_idx]
            else:
                base_node = None
            if base_node:
                bs = None
                code_before = ""
                code_after = ""
                if "project_path" in attrs:
                    proj_path = base_node.projectPath()
                if "cmake_options" in attrs:
                    opts = list(base_node.cmakeOptions())
                if "build_settings" in attrs:
                    bs = base_node.buildSettings()
                if "code_before_build" in attrs:
                    code_before = base_node.codeBeforeBuild()
                if "code_after_install" in attrs:
                    code_after = base_node.codeAfterInstall()
            else:
                bs = None
                code_before = ""
                code_after = ""

            if not node_name:
                node_name = f"Node_{self.scene.nodeCounter}"
            if any(n.title() == node_name for n in self.scene.nodes):
                QMessageBox.warning(self, "Warning", f"Node name '{node_name}' already exists.")
                return
            new_node = self.scene.addNewNode(node_name, opts, proj_path, bs)
            if code_before:
                new_node.setCodeBeforeBuild(code_before)
            if code_after:
                new_node.setCodeAfterInstall(code_after)
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

    def openNodePropertyDialog(self, node: NodeItem) -> None:
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
        self.topology_view.clear()
        if sorted_nodes is None:
            self.topology_view.addItem("Detected circular dependency, cannot build.")
        else:
            for i, node_item in enumerate(sorted_nodes):
                item = QListWidgetItem(f"{i+1}. {node_item.title()} (ID={node_item.id()})")
                item.setData(Qt.ItemDataRole.UserRole, node_item)
                self.topology_view.addItem(item)

    def onInspectorItemClicked(self, item: QListWidgetItem):
        node = item.data(Qt.ItemDataRole.UserRole)
        if node:
            self.view.resetTransform()
            self.view.centerOn(node)

    # ----------------------------------------------------------------
    # Asynchronous build flow
    # ----------------------------------------------------------------
    def runStage(
        self,
        stage: str = "build",
        start_node_id: int | None = None,
        end_node_id: int | None = None,
        force_first: bool = False,
        only_first: bool = False,
    ) -> None:
        """
        Build ProjectCommands for the given stage (configure/build/install) and
        execute them in a worker process.

        Parameters
        ----------
        stage : str
            Build stage (configure/build/install/all)
        start_node_id : int | None
            ID of the first node to run. If None, start from the beginning.
        end_node_id : int | None
            ID of the last node to run. If None, run until the end.
        force_first : bool
            If True, ignore start_node_id and always begin from the first node.
        only_first : bool
            If True, run only the first node in the range.
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
        elif start_node_id is not None:
            for idx, node_item in enumerate(sorted_nodes):
                if node_item.id() == start_node_id:
                    start_id = start_node_id
                    start_index = idx
                    break
            if start_id is None:
                QMessageBox.warning(self, "Warning", f"Start node ID {start_node_id} not found.")
                return

        end_index = len(sorted_nodes)
        if end_node_id is not None:
            found_end = False
            for idx, node_item in enumerate(sorted_nodes):
                if node_item.id() == end_node_id:
                    end_index = idx + 1
                    found_end = True
                    break
            if not found_end:
                QMessageBox.warning(self, "Warning", f"End node ID {end_node_id} not found.")
                return
        if end_index <= start_index:
            QMessageBox.warning(self, "Warning", "Invalid node range specified.")
            return

        project_commands = ProjectCommands(
            start_node_id=start_id if start_id is not None else -1,
            end_node_id=sorted_nodes[end_index-1].id() if end_index > 0 else -1,
            node_commands_list=[]
        )

        # For each node in sorted order within the specified range, build NodeCommands & CommandData
        for node_obj in sorted_nodes[start_index:end_index]:
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
            if stage in ("configure", "all") and node_obj.codeBeforeBuild().strip():
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

            if stage in ("configure", "all"):
                node_cmd.cmd_list.append(CommandData(
                    type="cmd", cmd=cmd_configure, display_name=f"Configure {project_name}"
                ))

            # Build command
            cmd_build = [
                "cmake", "--build", node_build_dir,
                "--config", build_type,
                "--parallel", str(multiprocessing.cpu_count())
            ]
            if stage in ("build", "all"):
                node_cmd.cmd_list.append(CommandData(
                    type="cmd", cmd=cmd_build, display_name=f"Build {project_name}"
                ))

            # Install command
            cmd_install = ["cmake", "--install", node_build_dir, "--config", build_type]
            if stage in ("install", "all"):
                node_cmd.cmd_list.append(CommandData(
                    type="cmd", cmd=cmd_install, display_name=f"Install {project_name}"
                ))

                if node_obj.codeAfterInstall().strip():
                    post_script_cmd = CommandData(
                        type="script",
                        cmd=node_obj.codeAfterInstall(),
                        display_name=f"Post-Install Script {project_name}"
                    )
                    node_cmd.cmd_list.append(post_script_cmd)

            project_commands.node_commands_list.append(node_cmd)
            if only_first:
                break

        if not project_commands.node_commands_list:
            QMessageBox.information(self, "Info", "No commands to run.")
            return

        # Setup progress bar
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

            # Stop worker process
            self.stopWorkerProcess()
            self.progress_bar.hide()

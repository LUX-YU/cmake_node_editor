"""
Main application window — thin shell after OCP refactoring.

Responsibilities:
- Create :class:`EditorContext` and :class:`ActionRegistry`
- Assemble the UI (docks, status bar)
- Register actions and wire signals/slots
- Coordinate dialogs and build orchestration
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget,
    QPlainTextEdit, QMessageBox,
    QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QDialog,
)

from .editor_context import EditorContext
from .action_registry import ActionRegistry
from .views.graphics_items import NodeItem
from .views.node_view import NodeView
from .models.data_classes import SubprocessLogData, SubprocessResponseData
from .services.cmake_command_builder import build_project_commands
from .dialogs.creation_dialog import NodeCreationDialog
from .dialogs.dependency_preview_dialog import DependencyPreviewDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.node_properties_dialog import NodePropertiesDialog
from .dialogs.batch_edit_dialog import BatchEditDialog
from .dialogs.node_range_dialog import NodeRangeDialog
from .constants import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE


class NodeEditorWindow(QMainWindow):
    """
    Main window: scene + view + docks + menus + build orchestration.
    """

    def __init__(self):
        super().__init__()
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Central mediator — owns scene, undo_stack, worker, settings
        self.ctx = EditorContext(self)

        # Convenience aliases
        self.scene = self.ctx.scene
        self._undo_stack = self.ctx.undo_stack

        # View
        self.view = NodeView(self.scene, self)
        self.view.createNodeRequested.connect(self._onCreateNodeAtPos)
        self._pending_scene_pos: QPointF | None = None
        self.setCentralWidget(self.view)

        # Docks
        self._initBuildOutputDock()
        self._initTopologyDock()

        # Action registry — declarative menus
        self._registry = ActionRegistry()
        self._registerActions()
        self._registry.build_menubar(self.menuBar(), self)

        # Status bar
        self._initStatusBar()

        # Topology callback
        self.scene.setTopologyCallback(self.updateTopologyView)

        # Selection tracking
        self.current_node: NodeItem | None = None
        self.scene.selectionChanged.connect(self._onSceneSelectionChanged)

        self.updateTopologyView()

        # Build state
        self._building = False
        self.current_progress = 0
        self.total_steps = 0

        # Wire EditorContext signals to window handlers
        self._connectContextSignals()

        # Restore persisted settings
        self._loadSettings()

        # Set initial title (reflects auto-opened project if any)
        self._updateTitle()

    # ----------------------------------------------------------------
    # Dock widgets
    # ----------------------------------------------------------------

    def _initBuildOutputDock(self):
        self.dock_build_output = QDockWidget("Build Output", self)
        self.dock_build_output.setObjectName("BuildOutputDock")
        self.build_output_text = QPlainTextEdit()
        self.build_output_text.setReadOnly(True)
        self.build_output_text.setMaximumBlockCount(10000)
        self.dock_build_output.setWidget(self.build_output_text)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_build_output)

    def _initTopologyDock(self):
        self.dock_topology = QDockWidget("Node Inspector", self)
        self.dock_topology.setObjectName("NodeInspectorDock")
        self.topology_view = QListWidget()
        self.topology_view.itemClicked.connect(self._onInspectorItemClicked)
        self.dock_topology.setWidget(self.topology_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_topology)

    # ----------------------------------------------------------------
    # Action registration (replaces hard-coded _initMenu)
    # ----------------------------------------------------------------

    def _registerActions(self):
        r = self._registry

        # -- File --
        r.register("file.save", "Save", "File", self._onQuickSave,
                    shortcut=QKeySequence.StandardKey.Save, order=10)
        r.register("file.save_as", "Save As...", "File", self._onSaveProject, order=20)
        r.register("file.load", "Load Project...", "File", self._onLoadProject, order=30)
        r.add_separator("File", order=40)
        r.register("file.settings", "Settings", "File", self._onSettings, order=50)

        # -- Project --
        r.register("project.full_configure", "Full Configure", "Project",
                    lambda: self.runStage(stage="configure", force_first=True), order=10)
        r.register("project.full_build", "Full Build", "Project",
                    lambda: self.runStage(stage="build", force_first=True), order=20)
        r.register("project.full_install", "Full Install", "Project",
                    lambda: self.runStage(stage="install", force_first=True), order=30)
        r.register("project.full_generate", "Full Generate", "Project",
                    lambda: self.runGenerate(force_first=True), order=40)
        r.add_separator("Project", order=50)
        r.register("project.cancel_build", "Cancel Build", "Project",
                    self._onCancelBuild, enabled=False, order=60)
        r.add_separator("Project", order=70)
        r.register("project.partial_configure", "Partial Configure", "Project",
                    lambda: self._onPartialStage("configure"), order=80)
        r.register("project.partial_build", "Partial Build", "Project",
                    lambda: self._onPartialStage("build"), order=90)
        r.register("project.partial_install", "Partial Install", "Project",
                    lambda: self._onPartialStage("install"), order=100)
        r.register("project.partial_generate", "Partial Generate", "Project",
                    lambda: self._onPartialStage("all"), order=110)

        # -- Edit --
        # Undo / Redo handled via QUndoStack's own actions
        act_undo = self._undo_stack.createUndoAction(self, "Undo")
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_redo = self._undo_stack.createRedoAction(self, "Redo")
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        # We register these as plain callbacks wrapping trigger
        r.register("edit.undo", "Undo", "Edit", act_undo.trigger,
                    shortcut=QKeySequence.StandardKey.Undo, order=10)
        r.register("edit.redo", "Redo", "Edit", act_redo.trigger,
                    shortcut=QKeySequence.StandardKey.Redo, order=20)
        r.add_separator("Edit", order=30)
        r.register("edit.add_node", "Add Node", "Edit", self.onAddNodeDialog, order=40)
        r.register("edit.edit_node", "Edit Node", "Edit",
                    lambda: self.openNodePropertyDialog(self.current_node),
                    enabled=False, order=50)
        r.register("edit.batch_edit", "Batch Edit", "Edit", self._onBatchEditNodes, order=60)
        r.register("edit.remove_node", "Remove Node", "Edit", self._onDeleteNode,
                    enabled=False, order=70)

        # -- Windows --
        r.register("windows.build_output", "Build Output", "Windows",
                    lambda checked: self.dock_build_output.setVisible(checked),
                    checkable=True, checked=True, order=10)
        r.register("windows.node_inspector", "Node Inspector", "Windows",
                    lambda checked: self.dock_topology.setVisible(checked),
                    checkable=True, checked=True, order=20)

    # ----------------------------------------------------------------
    # Signal wiring
    # ----------------------------------------------------------------

    def _connectContextSignals(self):
        """Wire EditorContext signals to window handlers."""
        self.ctx.nodeDoubleClicked.connect(self.openNodePropertyDialog)
        self.ctx.openPropertiesRequested.connect(self.openNodePropertyDialog)
        self.ctx.buildRequested.connect(self._onBuildSignal)
        self.ctx.generateRequested.connect(self._onGenerateSignal)
        self.ctx.buildToRequested.connect(self._onBuildToSignal)
        self.ctx.cancelBuildRequested.connect(self._onCancelBuild)

    def _onBuildSignal(self, stage: str, kwargs: dict):
        """Slot for ``EditorContext.buildRequested``."""
        self.runStage(stage=stage, **kwargs)

    def _onGenerateSignal(self, kwargs: dict):
        """Slot for ``EditorContext.generateRequested``."""
        self.runGenerate(**kwargs)

    def _onBuildToSignal(self, stage: str, target_node):
        """Slot for ``EditorContext.buildToRequested``.

        Computes the minimal ancestor dependency order for *target_node*,
        shows a confirmation dialog, then executes the build.
        """
        ordered = self.scene.ancestorSubgraphSort(target_node)
        if ordered is None:
            QMessageBox.critical(
                self, "Error",
                "Detected circular dependency — cannot compute build order."
            )
            return

        dlg = DependencyPreviewDialog(stage, target_node, ordered, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Build using the minimal subgraph order directly
        self._runStageWithNodes(stage, ordered)

    def _runStageWithNodes(self, stage: str, ordered_nodes: list) -> None:
        """Run a build *stage* on an explicit list of already-ordered nodes."""
        if self._building:
            QMessageBox.warning(self, "Warning", "A build is already in progress.")
            return

        self.build_output_text.clear()

        result = build_project_commands(
            ordered_nodes,
            stage=stage,
            start_index=0,
            end_index=len(ordered_nodes),
            start_node_id=ordered_nodes[0].id() if ordered_nodes else -1,
            only_first=False,
        )
        if isinstance(result, str):
            QMessageBox.critical(self, "Error", result)
            return

        project_commands = result

        # Progress bar
        self.total_steps = len(project_commands.node_commands_list)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.current_progress = 0

        # Delegate to WorkerManager
        self._building = True
        self._registry.set_enabled("project.cancel_build", True)
        self.ctx.worker.start()
        self.ctx.worker.create_listener(self._onWorkerLog, self._onWorkerResponse)
        self.ctx.worker.send(project_commands)
        self.build_output_text.appendPlainText("[Main] Sent ProjectCommands to worker.")

    def _initStatusBar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(1)
        self.progress_bar.hide()
        self.statusBar().addPermanentWidget(self.progress_bar)

    # ----------------------------------------------------------------
    # Window events
    # ----------------------------------------------------------------

    def closeEvent(self, event):
        self._saveSettings()
        self.ctx.worker.stop()
        super().closeEvent(event)

    # ----------------------------------------------------------------
    # Title
    # ----------------------------------------------------------------

    def _updateTitle(self):
        """Set the window title, appending the current file name if any."""
        if self.ctx.current_file:
            name = os.path.basename(self.ctx.current_file)
            self.setWindowTitle(f"{WINDOW_TITLE} — {name}")
        else:
            self.setWindowTitle(WINDOW_TITLE)

    # ----------------------------------------------------------------
    # File actions
    # ----------------------------------------------------------------

    def _onQuickSave(self):
        """Save to the current file; fall back to Save As if no path yet."""
        if self.ctx.current_file:
            err = self.scene.saveProjectToJson(self.ctx.current_file, None)
            if err:
                QMessageBox.critical(self, "Error", err)
            else:
                name = os.path.basename(self.ctx.current_file)
                self.statusBar().showMessage(f"Saved to {name}", 3000)
        else:
            self._onSaveProject()

    def _onSaveProject(self):
        default_dir = os.path.dirname(self.ctx.current_file) if self.ctx.current_file else "."
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Project", default_dir, "JSON Files (*.json)")
        if not filepath:
            return
        err = self.scene.saveProjectToJson(filepath, None)
        if err:
            QMessageBox.critical(self, "Error", err)
        else:
            self.ctx.current_file = filepath
            self._updateTitle()
            QMessageBox.information(self, "Info", "Project has been saved!")

    def _onLoadProject(self):
        default_dir = os.path.dirname(self.ctx.current_file) if self.ctx.current_file else "."
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Project", default_dir, "JSON Files (*.json)")
        if not filepath:
            return
        self.scene.loadProjectFromJson(filepath)
        self.ctx.current_file = filepath
        self._undo_stack.clear()
        self._updateTitle()
        QMessageBox.information(self, "Info", "Project loaded!")
        self.updateTopologyView()

    def _onSettings(self):
        current_style = QApplication.style().objectName()
        dlg = SettingsDialog(current_style, self.scene.gridOpacity(), self.scene.linkColor(), self)
        if dlg.exec():
            style_name, opacity, link_color = dlg.getValues()
            QApplication.setStyle(style_name)
            self.scene.setGridOpacity(opacity)
            self.scene.setLinkColor(link_color)

    # ----------------------------------------------------------------
    # QSettings persistence
    # ----------------------------------------------------------------

    def _loadSettings(self):
        s = self.ctx.settings
        style = s.value("style", "")
        if style:
            QApplication.setStyle(style)
        opacity = s.value("grid_opacity", None)
        if opacity is not None:
            self.scene.setGridOpacity(float(opacity))
        link = s.value("link_color", None)
        if link is not None:
            self.scene.setLinkColor(QColor(link))
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        state = s.value("windowState")
        if state:
            self.restoreState(state)
        # Auto-open last project
        last = s.value("last_project", "")
        if last and os.path.isfile(last):
            try:
                self.scene.loadProjectFromJson(last)
                self.ctx.current_file = last
                self._undo_stack.clear()
                self.updateTopologyView()
                self.statusBar().showMessage(f"Restored: {last}", 5000)
            except Exception as exc:
                self.statusBar().showMessage(
                    f"Failed to restore last project: {exc}", 5000
                )

    def _saveSettings(self):
        s = self.ctx.settings
        s.setValue("style", QApplication.style().objectName())
        s.setValue("grid_opacity", self.scene.gridOpacity())
        s.setValue("link_color", self.scene.linkColor().name())
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        s.setValue("last_project", self.ctx.current_file or "")

    # ----------------------------------------------------------------
    # Node operations
    # ----------------------------------------------------------------

    def _onCreateNodeAtPos(self, scene_pos: QPointF):
        """Store the click position, then open the creation dialog."""
        self._pending_scene_pos = scene_pos
        self.onAddNodeDialog()

    def onAddNodeDialog(self):
        dlg = NodeCreationDialog(self, existing_nodes=self.scene.nodes)
        if dlg.exec() != dlg.DialogCode.Accepted:
            self._pending_scene_pos = None
            return

        r = dlg.getResult()

        node_name = r.node_name
        if not node_name:
            node_name = f"Node_{self.scene.nodeCounter}"
        if any(n.title() == node_name for n in self.scene.nodes):
            QMessageBox.warning(self, "Warning", f"Node name '{node_name}' already exists.")
            self._pending_scene_pos = None
            return

        pos = self._pending_scene_pos
        self._pending_scene_pos = None
        new_node = self.scene.addNewNode(
            node_name, [], r.project_path, r.build_settings, pos=pos,
        )
        new_node.setBuildSystem(r.build_system)

        # Strategy-specific inheritance (delegated to the strategy)
        if r.inherit_source and r.inherit_keys:
            from .services.build_strategies import get_strategy
            strategy = get_strategy(r.build_system)
            strategy.copy_node_data(new_node, r.inherit_source, r.inherit_keys)

        if r.code_before_build:
            new_node.setCodeBeforeBuild(r.code_before_build)
        if r.code_after_install:
            new_node.setCodeAfterInstall(r.code_after_install)
        self.scene.clearSelection()
        new_node.setSelected(True)
        self._undo_stack.clear()  # complex creation — reset undo stack

    def _onDeleteNode(self):
        if self.current_node:
            self.ctx.undo_remove_node(self.current_node)
            self.current_node = None

    def _onSceneSelectionChanged(self):
        sel = self.scene.selectedItems()
        if sel and isinstance(sel[0], NodeItem):
            self.current_node = sel[0]
            self._registry.set_enabled("edit.remove_node", True)
            self._registry.set_enabled("edit.edit_node", True)
        else:
            self.current_node = None
            self._registry.set_enabled("edit.remove_node", False)
            self._registry.set_enabled("edit.edit_node", False)

    def openNodePropertyDialog(self, node: NodeItem | None) -> None:
        if not node:
            return
        dlg = NodePropertiesDialog(node, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            dlg.applyToNode()

    def _onBatchEditNodes(self):
        dlg = BatchEditDialog(self.scene.nodes, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            if dlg.applyToNodes():
                self.updateTopologyView()

    # ----------------------------------------------------------------
    # Partial stage helpers
    # ----------------------------------------------------------------

    def _onPartialStage(self, stage: str) -> None:
        sorted_nodes = self.scene.topologicalSort()
        if not sorted_nodes:
            QMessageBox.information(self, "Info", "No nodes available")
            return
        ids = [n.id() for n in sorted_nodes]
        dlg = NodeRangeDialog(min(ids), max(ids), self, valid_ids=set(ids))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        s_id, e_id = dlg.getValues()
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

    def _onInspectorItemClicked(self, item: QListWidgetItem):
        node = item.data(Qt.ItemDataRole.UserRole)
        if node:
            self.view.resetTransform()
            self.view.centerOn(node)

    # ----------------------------------------------------------------
    # Build orchestration
    # ----------------------------------------------------------------

    def runGenerate(
        self,
        start_node_id: int | None = None,
        end_node_id: int | None = None,
        force_first: bool = False,
        only_first: bool = False,
    ) -> None:
        self.runStage(
            stage="all",
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            force_first=force_first,
            only_first=only_first,
        )

    def runStage(
        self,
        stage: str = "build",
        start_node_id: int | None = None,
        end_node_id: int | None = None,
        force_first: bool = False,
        only_first: bool = False,
    ) -> None:
        if self._building:
            QMessageBox.warning(self, "Warning", "A build is already in progress.")
            return

        self.build_output_text.clear()

        sorted_nodes = self.scene.topologicalSort()
        if sorted_nodes is None:
            QMessageBox.critical(self, "Error", "Detected circular dependency, cannot build.")
            return

        # Determine start / end indices
        start_id = None
        start_index = 0
        if force_first:
            start_id = sorted_nodes[0].id() if sorted_nodes else -1
        elif start_node_id is not None:
            for idx, n in enumerate(sorted_nodes):
                if n.id() == start_node_id:
                    start_id = start_node_id
                    start_index = idx
                    break
            if start_id is None:
                QMessageBox.warning(self, "Warning", f"Start node ID {start_node_id} not found.")
                return

        end_index = len(sorted_nodes)
        if end_node_id is not None:
            found = False
            for idx, n in enumerate(sorted_nodes):
                if n.id() == end_node_id:
                    end_index = idx + 1
                    found = True
                    break
            if not found:
                QMessageBox.warning(self, "Warning", f"End node ID {end_node_id} not found.")
                return

        if end_index <= start_index:
            QMessageBox.warning(self, "Warning", "Invalid node range specified.")
            return

        # Delegate to CMakeCommandBuilder
        result = build_project_commands(
            sorted_nodes,
            stage=stage,
            start_index=start_index,
            end_index=end_index,
            start_node_id=start_id,
            only_first=only_first,
        )
        if isinstance(result, str):
            QMessageBox.critical(self, "Error", result)
            return

        project_commands = result

        # Progress bar
        self.total_steps = len(project_commands.node_commands_list)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.current_progress = 0

        # Delegate to WorkerManager
        self._building = True
        self._registry.set_enabled("project.cancel_build", True)
        self.ctx.worker.start()
        self.ctx.worker.create_listener(self._onWorkerLog, self._onWorkerResponse)
        self.ctx.worker.send(project_commands)
        self.build_output_text.appendPlainText("[Main] Sent ProjectCommands to worker.")

    # ----------------------------------------------------------------
    # Worker callbacks
    # ----------------------------------------------------------------

    def _onWorkerLog(self, logData: SubprocessLogData):
        self.build_output_text.appendPlainText(logData.log)

    def _onCancelBuild(self):
        """User-initiated build cancellation."""
        if self._building:
            self.build_output_text.appendPlainText("[Main] Build cancelled by user.")
            self._finishBuild()

    def _finishBuild(self):
        """Common cleanup after build completes or is cancelled."""
        self.ctx.worker.stop()
        self._building = False
        self._registry.set_enabled("project.cancel_build", False)
        self.progress_bar.hide()

    def _onWorkerResponse(self, respData: SubprocessResponseData):
        if respData.index >= 0:
            result_str = "SUCCESS" if respData.result else "FAILED"
            self.build_output_text.appendPlainText(
                f"[Node {respData.index}] {result_str}"
            )
            self.current_progress += 1
            self.progress_bar.setValue(self.current_progress)

        if respData.index == -1:
            if respData.result:
                self.build_output_text.appendPlainText("\n=== Build Completed! ===")
            else:
                self.build_output_text.appendPlainText("\n=== Build Failed! ===")
            self._finishBuild()

"""
NodeView — custom ``QGraphicsView`` with zoom, panning, and context menus.

Extracted from the monolithic ``node_editor_window.py``.
"""

from __future__ import annotations

import os
import re
import subprocess

from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent, QDesktopServices
from PyQt6.QtWidgets import QGraphicsView, QMenu, QMessageBox

from ..views.graphics_items import NodeItem, Edge
from ..constants import ZOOM_SCALE_FACTOR
from ..services.editor_detection import detect_editors


class NodeView(QGraphicsView):
    """A ``QGraphicsView`` that holds a :class:`NodeScene`."""

    createNodeRequested = pyqtSignal(QPointF)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._panning = False
        self._last_mouse_pos = None
        self._press_pos = None
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

    # -- Zoom --

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.scale(ZOOM_SCALE_FACTOR, ZOOM_SCALE_FACTOR)
        else:
            self.scale(1.0 / ZOOM_SCALE_FACTOR, 1.0 / ZOOM_SCALE_FACTOR)

    # -- Right-click panning --

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
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
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            moved = (event.pos() - self._press_pos).manhattanLength() if self._press_pos else 0
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._press_pos = None
            if moved < 4:
                self.openContextMenu(event.globalPosition().toPoint(), event.pos())
        else:
            super().mouseReleaseEvent(event)

    # -- Context menu --

    def openContextMenu(self, global_pos, view_pos):
        scene_pos = self.mapToScene(view_pos)
        item = self.scene().itemAt(scene_pos, self.transform())
        # Walk up the parent chain so clicking on a child (e.g. text label)
        # still resolves to the owning NodeItem.
        while item and not isinstance(item, NodeItem):
            item = item.parentItem()
        menu = QMenu(self)
        ctx = getattr(self.scene(), 'context', None)

        if isinstance(item, NodeItem):
            act_cfg_node = menu.addAction("Configure Node")
            act_build_node = menu.addAction("Build Node")
            act_install_node = menu.addAction("Install Node")
            menu.addSeparator()
            act_cfg_from = menu.addAction("Configure From This")
            act_build_from = menu.addAction("Build From This")
            act_install_from = menu.addAction("Install From This")
            act_gen_to = menu.addAction("Generate To This")
            menu.addSeparator()
            act_cfg_to = menu.addAction("Configure To This (deps only)")
            act_build_to = menu.addAction("Build To This (deps only)")
            act_install_to = menu.addAction("Install To This (deps only)")
            act_gen_to_deps = menu.addAction("Generate To This (deps only)")
            menu.addSeparator()
            act_open_dir = menu.addAction("Open Project Directory")
            act_open_build = menu.addAction("Open Build Directory")
            act_open_install = menu.addAction("Open Install Directory")
            # -- Open in Editor submenu --
            editor_actions = self._buildEditorMenu(menu, item.projectPath())
            menu.addSeparator()
            act_prop = menu.addAction("Properties")
            action = menu.exec(global_pos)
            if not action:
                return
            if action == act_prop and ctx:
                ctx.openPropertiesRequested.emit(item)
            elif action == act_open_dir:
                self._openFolder(item.projectPath(), "project directory")
            elif action == act_open_build:
                self._openFolder(
                    self._resolveNodeBuildDir(item, ctx), "build directory",
                )
            elif action == act_open_install:
                self._openFolder(
                    self._resolveNodeInstallDir(item, ctx), "install directory",
                )
            elif action in editor_actions:
                self._launchEditor(editor_actions[action], item.projectPath())
            elif ctx:
                if action == act_cfg_node:
                    ctx.buildRequested.emit("configure", {"start_node_id": item.id(), "only_first": True})
                elif action == act_build_node:
                    ctx.buildRequested.emit("build", {"start_node_id": item.id(), "only_first": True})
                elif action == act_install_node:
                    ctx.buildRequested.emit("install", {"start_node_id": item.id(), "only_first": True})
                elif action == act_cfg_from:
                    ctx.buildRequested.emit("configure", {"start_node_id": item.id()})
                elif action == act_build_from:
                    ctx.buildRequested.emit("build", {"start_node_id": item.id()})
                elif action == act_install_from:
                    ctx.buildRequested.emit("install", {"start_node_id": item.id()})
                elif action == act_gen_to:
                    ctx.generateRequested.emit({"end_node_id": item.id()})
                elif action == act_cfg_to:
                    ctx.buildToRequested.emit("configure", item)
                elif action == act_build_to:
                    ctx.buildToRequested.emit("build", item)
                elif action == act_install_to:
                    ctx.buildToRequested.emit("install", item)
                elif action == act_gen_to_deps:
                    ctx.buildToRequested.emit("all", item)
        else:
            act_new = menu.addAction("Create Node")
            if ctx:
                menu.addSeparator()
                act_full_cfg = menu.addAction("Full Configure")
                act_full_build = menu.addAction("Full Build")
                act_full_install = menu.addAction("Full Install")
                act_full_gen = menu.addAction("Full Generate")
            action = menu.exec(global_pos)
            if not action:
                return
            if action == act_new:
                self.createNodeRequested.emit(scene_pos)
            elif ctx:
                if action == act_full_cfg:
                    ctx.buildRequested.emit("configure", {"force_first": True})
                elif action == act_full_build:
                    ctx.buildRequested.emit("build", {"force_first": True})
                elif action == act_full_install:
                    ctx.buildRequested.emit("install", {"force_first": True})
                elif action == act_full_gen:
                    ctx.generateRequested.emit({"force_first": True})

    # -- Editor helpers --

    @staticmethod
    def _buildEditorMenu(parent_menu: QMenu, proj_dir: str) -> dict:
        """Add 'Open in <editor>' actions; return {QAction: exe_path} map."""
        editors = detect_editors()
        action_map: dict = {}
        if not editors:
            act = parent_menu.addAction("Open in Editor (none detected)")
            act.setEnabled(False)
        elif len(editors) == 1:
            name, exe = editors[0]
            act = parent_menu.addAction(f"Open in {name}")
            action_map[act] = exe
        else:
            sub = parent_menu.addMenu("Open in Editor")
            for name, exe in editors:
                act = sub.addAction(name)
                action_map[act] = exe
        return action_map

    @staticmethod
    def _launchEditor(exe: str, proj_dir: str) -> None:
        if proj_dir and os.path.isdir(proj_dir):
            try:
                subprocess.Popen([exe, proj_dir],
                                 creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0))
            except OSError as e:
                QMessageBox.warning(None, "Error", f"Failed to launch editor:\n{e}")

    # -- Open folder helpers --

    @staticmethod
    def _openFolder(path: str, label: str) -> None:
        """Open *path* in the system file manager, warn if it doesn't exist."""
        from PyQt6.QtCore import QUrl
        if path and os.path.isdir(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(
                None, "Not Found",
                f"The {label} does not exist yet:\n{path}",
            )

    @staticmethod
    def _resolveNodeBuildDir(node: NodeItem, ctx) -> str:
        bs = node.buildSettings()
        build_type = ctx.global_build_type if ctx else bs.build_type
        safe_name = re.sub(r"[^\w\-.]", "_", node.title())
        return os.path.join(bs.build_dir.format(build_type=build_type), safe_name)

    @staticmethod
    def _resolveNodeInstallDir(node: NodeItem, ctx) -> str:
        bs = node.buildSettings()
        build_type = ctx.global_build_type if ctx else bs.build_type
        return bs.install_dir.format(build_type=build_type)

    # -- Delete key --

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            scene = self.scene()
            ctx = getattr(scene, 'context', None)
            for item in scene.selectedItems():
                if isinstance(item, Edge):
                    if ctx:
                        ctx.undo_remove_edge(item)
                    else:
                        scene.removeEdge(item)
                elif isinstance(item, NodeItem):
                    if ctx:
                        ctx.undo_remove_node(item)
                    else:
                        scene.removeNode(item)
            event.accept()
        else:
            super().keyPressEvent(event)

"""
NodeView — custom ``QGraphicsView`` with zoom, panning, and context menus.

Extracted from the monolithic ``node_editor_window.py``.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent, QDesktopServices
from PyQt6.QtWidgets import QGraphicsView, QMenu, QMessageBox

from ..views.graphics_items import NodeItem, Edge
from ..constants import ZOOM_SCALE_FACTOR


class NodeView(QGraphicsView):
    """A ``QGraphicsView`` that holds a :class:`NodeScene`."""

    createNodeRequested = pyqtSignal()

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._panning = False
        self._last_mouse_pos = None
        self._press_pos = None
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

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

    def showContextMenu(self, pos):
        self._panning = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.openContextMenu(self.mapToGlobal(pos), pos)

    def openContextMenu(self, global_pos, view_pos):
        scene_pos = self.mapToScene(view_pos)
        item = self.scene().itemAt(scene_pos, self.transform())
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
            act_open_dir = menu.addAction("Open Project Directory")
            menu.addSeparator()
            act_prop = menu.addAction("Properties")
            action = menu.exec(global_pos)
            if not action:
                return
            if action == act_prop and ctx:
                ctx.openPropertiesRequested.emit(item)
            elif action == act_open_dir:
                proj_dir = item.projectPath()
                if proj_dir and os.path.isdir(proj_dir):
                    from PyQt6.QtCore import QUrl
                    QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(proj_dir)))
                else:
                    QMessageBox.warning(self, "Warning", "Invalid project directory")
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
        else:
            act_new = menu.addAction("Create Node")
            action = menu.exec(global_pos)
            if action == act_new:
                self.createNodeRequested.emit()

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

"""
Editor context — the central mediator for the node editor application.

All modules hold a reference to the single :class:`EditorContext` instance and
communicate through its Qt signals instead of calling each other directly.
This eliminates ``parent()`` / ``hasattr`` coupling and makes every feature
independently testable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from PyQt6.QtGui import QUndoStack

from .scene.node_scene import NodeScene
from .services.worker_manager import WorkerManager
from .undo_commands import (
    AddNodeCommand, RemoveNodeCommand,
    AddEdgeCommand, RemoveEdgeCommand,
)

if TYPE_CHECKING:
    from .views.graphics_items import NodeItem, Edge, Pin
    from .models.data_classes import BuildSettings


class EditorContext(QObject):
    """
    Shared application context — the single source of truth.

    Subsystems (views, dialogs, services) connect to the signals below
    instead of reaching up to the main window via ``parent()`` or
    ``hasattr`` checks.  The main window is just one of many listeners.
    """

    # -- Graph editing signals --
    nodeDoubleClicked       = pyqtSignal(object)        # NodeItem
    createNodeRequested     = pyqtSignal()              # "Add Node" trigger
    deleteNodeRequested     = pyqtSignal(object)        # NodeItem
    openPropertiesRequested = pyqtSignal(object)        # NodeItem

    # -- Build signals --
    buildRequested        = pyqtSignal(str, dict)       # (stage, kwargs)
    generateRequested     = pyqtSignal(dict)            # kwargs
    buildToRequested      = pyqtSignal(str, object)     # (stage, NodeItem)
    cancelBuildRequested  = pyqtSignal()

    # -- File signals --
    saveRequested         = pyqtSignal()
    saveAsRequested       = pyqtSignal()
    loadRequested         = pyqtSignal()

    # -- Selection --
    selectionChanged      = pyqtSignal(object)          # NodeItem | None

    # -- Status messages --
    statusMessage         = pyqtSignal(str, int)        # (text, timeout_ms)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.undo_stack = QUndoStack(self)
        self.scene = NodeScene()
        self.scene.setContext(self)               # back-reference
        self.worker = WorkerManager()
        self.settings = QSettings("CMakeNodeEditor", "CMakeNodeEditor")

        # Mutable state shared across the app
        self.building: bool = False
        self.current_file: str | None = None
        self.current_node: object | None = None   # NodeItem | None
        self.global_build_type: str | None = None  # None = use per-node setting

    # ------------------------------------------------------------------
    # Undoable convenience methods — used by views instead of touching
    # the undo stack directly.  Undo commands themselves call the raw
    # scene methods (addEdge / removeEdge / ...) so there is no recursion.
    # ------------------------------------------------------------------

    def undo_add_edge(self, source_pin: "Pin", target_pin: "Pin") -> None:
        self.undo_stack.push(AddEdgeCommand(self.scene, source_pin, target_pin))

    def undo_remove_edge(self, edge: "Edge") -> None:
        self.undo_stack.push(RemoveEdgeCommand(self.scene, edge))

    def undo_add_node(
        self,
        title: str,
        cmake_options: list[str],
        project_path: str,
        build_settings: "BuildSettings | None" = None,
    ) -> "NodeItem | None":
        cmd = AddNodeCommand(self.scene, title, cmake_options, project_path, build_settings)
        self.undo_stack.push(cmd)
        return cmd.node

    def undo_remove_node(self, node: "NodeItem") -> None:
        self.undo_stack.push(RemoveNodeCommand(self.scene, node))

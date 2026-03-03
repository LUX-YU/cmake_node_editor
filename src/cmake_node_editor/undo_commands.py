"""
QUndoCommand implementations for node and edge operations.

These commands enable Ctrl+Z / Ctrl+Y undo/redo for all graph mutations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from .scene.node_scene import NodeScene
    from .views.graphics_items import NodeItem, Edge, Pin
    from .models.data_classes import BuildSettings


class AddNodeCommand(QUndoCommand):
    """Undoable command: add a node to the scene."""

    def __init__(
        self,
        scene: "NodeScene",
        title: str,
        cmake_options: list[str],
        project_path: str,
        build_settings: "BuildSettings | None" = None,
        description: str = "Add Node",
    ):
        super().__init__(description)
        self._scene = scene
        self._title = title
        self._cmake_options = cmake_options
        self._project_path = project_path
        self._build_settings = build_settings
        self._node: NodeItem | None = None

    def redo(self):
        self._node = self._scene.addNewNode(
            self._title,
            self._cmake_options,
            self._project_path,
            self._build_settings,
        )

    def undo(self):
        if self._node is not None:
            self._scene.removeNode(self._node)
            self._node = None

    @property
    def node(self) -> "NodeItem | None":
        return self._node


class RemoveNodeCommand(QUndoCommand):
    """Undoable command: remove a node (and its edges) from the scene."""

    def __init__(self, scene: "NodeScene", node: "NodeItem", description: str = "Remove Node"):
        super().__init__(description)
        self._scene = scene
        self._node = node
        # Snapshot the node data so we can recreate it
        self._node_data = node.nodeData()
        # Record connected edges as (src_node_id, dst_node_id) so we can reconnect
        self._edge_pairs: list[tuple[int, int]] = []
        for e in list(scene.edges):
            sp = e.sourcePin()
            tp = e.targetPin()
            if sp and tp:
                if sp.parent_node is node or tp.parent_node is node:
                    self._edge_pairs.append((sp.parent_node.id(), tp.parent_node.id()))

    def redo(self):
        self._scene.removeNode(self._node)

    def undo(self):
        from .views.graphics_items import NodeItem as NI
        import copy
        # Re-create the node from its saved data
        new_node = NI(data=copy.deepcopy(self._node_data))
        self._scene.restoreNode(new_node)

        # Rebuild node map for edge reconnection
        node_map = {n.id(): n for n in self._scene.nodes}
        for src_id, dst_id in self._edge_pairs:
            if src_id in node_map and dst_id in node_map:
                self._scene.addEdge(
                    node_map[src_id].output_pin,
                    node_map[dst_id].input_pin,
                )

        self._node = new_node


class AddEdgeCommand(QUndoCommand):
    """Undoable command: add an edge between two pins."""

    def __init__(self, scene: "NodeScene", source_pin: "Pin", target_pin: "Pin",
                 description: str = "Add Edge"):
        super().__init__(description)
        self._scene = scene
        self._src_node_id = source_pin.parent_node.id()
        self._dst_node_id = target_pin.parent_node.id()
        self._edge: Edge | None = None

    def redo(self):
        node_map = {n.id(): n for n in self._scene.nodes}
        src = node_map.get(self._src_node_id)
        dst = node_map.get(self._dst_node_id)
        if src and dst:
            self._scene.addEdge(src.output_pin, dst.input_pin)
            # Find the edge we just added
            for e in self._scene.edges:
                sp = e.sourcePin()
                tp = e.targetPin()
                if sp and tp and sp.parent_node.id() == self._src_node_id \
                   and tp.parent_node.id() == self._dst_node_id:
                    self._edge = e
                    break

    def undo(self):
        if self._edge and self._edge in self._scene.edges:
            self._scene.removeEdge(self._edge)
            self._edge = None


class RemoveEdgeCommand(QUndoCommand):
    """Undoable command: remove an edge."""

    def __init__(self, scene: "NodeScene", edge: "Edge", description: str = "Remove Edge"):
        super().__init__(description)
        self._scene = scene
        sp = edge.sourcePin()
        tp = edge.targetPin()
        self._src_node_id = sp.parent_node.id() if sp else -1
        self._dst_node_id = tp.parent_node.id() if tp else -1

    def redo(self):
        # Find and remove by node IDs
        for e in list(self._scene.edges):
            sp = e.sourcePin()
            tp = e.targetPin()
            if sp and tp and sp.parent_node.id() == self._src_node_id \
               and tp.parent_node.id() == self._dst_node_id:
                self._scene.removeEdge(e)
                break

    def undo(self):
        node_map = {n.id(): n for n in self._scene.nodes}
        src = node_map.get(self._src_node_id)
        dst = node_map.get(self._dst_node_id)
        if src and dst:
            self._scene.addEdge(src.output_pin, dst.input_pin)

"""
NodeScene — Qt graphics scene for the node editor.

After the refactoring the scene delegates data management to
:class:`GraphModel` and serialization to the ``serialization`` module.
It still owns the visual ``QGraphicsScene`` lifecycle (add/remove items,
background grid drawing, link color).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, QLineF
from PyQt6.QtGui import QBrush, QPen, QColor
from PyQt6.QtWidgets import QGraphicsScene

from ..views.graphics_items import NodeItem, Edge, Pin
from ..models.data_classes import NodeData, BuildSettings
from ..scene.graph_model import GraphModel
from ..scene.serialization import save_project, load_project
from ..constants import (
    DEFAULT_GRID_OPACITY, GRID_SIZE,
)


class NodeScene(QGraphicsScene):
    """
    Qt graphics scene that renders nodes and edges and manages the
    underlying :class:`GraphModel`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Let Qt auto-compute scene rect from item bounding boxes
        # by not setting a fixed scene rect.

        self._model = GraphModel()
        self._context = None            # set by EditorContext.setContext()
        self.link_color = QColor(Qt.GlobalColor.black)
        self.grid_opacity = DEFAULT_GRID_OPACITY

    # -- Context accessor (replaces parent() / hasattr pattern) --

    def setContext(self, ctx):
        """Called once by :class:`EditorContext` after construction."""
        self._context = ctx

    @property
    def context(self):
        """Return the :class:`EditorContext` mediator, or *None*."""
        return self._context

    # -- Convenience accessors delegating to the model --

    @property
    def nodes(self) -> list[NodeItem]:
        return self._model.nodes

    @property
    def edges(self) -> list[Edge]:
        return self._model.edges

    @property
    def nodeCounter(self) -> int:
        return self._model.node_counter

    @nodeCounter.setter
    def nodeCounter(self, value: int):
        self._model.node_counter = value

    # -- Topology callback delegation --

    def setTopologyCallback(self, func):
        self._model.setTopologyCallback(func)

    def notifyTopologyChanged(self):
        self._model.notifyTopologyChanged()

    # -- Background grid --

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)

        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)

        painter.save()
        color = QColor(Qt.GlobalColor.lightGray)
        color.setAlphaF(self.grid_opacity)
        painter.setPen(QPen(color, 1))

        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += GRID_SIZE

        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += GRID_SIZE

        painter.restore()

    # -- Grid / color settings --

    def setGridOpacity(self, value: float):
        self.grid_opacity = max(0.0, min(1.0, value))
        self.update()

    def gridOpacity(self) -> float:
        return self.grid_opacity

    def setLinkColor(self, color: QColor):
        self.link_color = color
        for e in self._model.edges:
            e.updateColor()

    def linkColor(self) -> QColor:
        return self.link_color

    # -- Node CRUD --

    def addNewNode(
        self,
        title: str,
        cmake_options: list[str],
        project_path: str,
        build_settings: BuildSettings | None = None,
    ) -> NodeItem:
        node_id = self._model.next_id()
        if build_settings is None:
            build_settings = self._model.default_build_settings()
        new_node = NodeItem(
            node_id=node_id,
            title=title,
            cmake_options=cmake_options,
            project_path=project_path,
            data=None,
        )
        new_node.setBuildSettings(build_settings)

        pos = self._model.advance_node_pos()
        new_node.setPos(pos)
        new_node.nodeData().pos_x = pos.x()
        new_node.nodeData().pos_y = pos.y()

        self.addItem(new_node)
        self._model.nodes.append(new_node)
        self._model.notifyTopologyChanged()
        return new_node

    def removeNode(self, node_item: NodeItem):
        if node_item in self._model.nodes:
            edges_to_remove = [
                e for e in self._model.edges
                if (e.sourcePin() and e.sourcePin().parent_node is node_item)
                or (e.targetPin() and e.targetPin().parent_node is node_item)
            ]
            for e in edges_to_remove:
                self.removeEdge(e)
            self.removeItem(node_item)
            self._model.nodes.remove(node_item)
            self._model.notifyTopologyChanged()

    def restoreNode(self, node_item: NodeItem) -> None:
        """
        Re-add a previously removed node to the scene.

        Used by :class:`RemoveNodeCommand.undo` so that undo commands
        never need to touch ``_model`` directly.
        """
        self.addItem(node_item)
        self._model.nodes.append(node_item)
        self._model.notifyTopologyChanged()

    # -- Edge CRUD --

    def addEdge(self, source_pin: Pin, target_pin: Pin) -> None:
        if self._model.is_self_loop(source_pin, target_pin):
            return
        if self._model.has_edge(source_pin, target_pin):
            return

        edge = Edge(source_pin, target_pin, is_temp=False)
        self.addItem(edge)
        self._model.edges.append(edge)
        edge.updateColor()
        edge.updatePath()
        self._model.notifyTopologyChanged()

    def removeEdge(self, edge: Edge) -> None:
        if edge in self._model.edges:
            self.removeItem(edge)
            self._model.edges.remove(edge)
            self._model.notifyTopologyChanged()

    # -- Topology --

    def topologicalSort(self) -> list[NodeItem] | None:
        return self._model.topologicalSort()

    # -- Serialization --

    def saveProjectToJson(self, filepath: str, start_node_id: int | None = None) -> str | None:
        return save_project(filepath, self._model.nodes, self._model.edges, start_node_id)

    def loadProjectFromJson(self, filepath: str) -> dict:
        global_cfg, node_data_list, edge_dicts = load_project(filepath)
        self.clearScene()

        self._model.node_counter = 1
        for nd in node_data_list:
            self._model.node_counter = max(self._model.node_counter, nd.node_id + 1)

        node_map: dict[int, NodeItem] = {}
        for nd in node_data_list:
            node_item = NodeItem(data=nd)
            self.addItem(node_item)
            self._model.nodes.append(node_item)
            node_map[node_item.id()] = node_item

        for ed in edge_dicts:
            src_id = ed["source_node_id"]
            dst_id = ed["target_node_id"]
            if src_id in node_map and dst_id in node_map:
                self.addEdge(node_map[src_id].output_pin, node_map[dst_id].input_pin)

        self._model.notifyTopologyChanged()
        return global_cfg

    def clearScene(self):
        for e in self._model.edges[:]:
            self.removeEdge(e)
        for n in self._model.nodes[:]:
            self.removeNode(n)
        self._model.nodes.clear()
        self._model.edges.clear()

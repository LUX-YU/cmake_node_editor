import os
import json
from collections import deque

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QBrush, QPen, QPainterPath, QLineF
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsRectItem, QGraphicsPathItem,
    QGraphicsItem, QGraphicsTextItem
)

from dataclasses import asdict
import os
from .datas import NodeData, EdgeData, BuildSettings


class Pin(QGraphicsRectItem):
    """
    Represents a pin on a node (either input or output). 
    By dragging this pin, the user can create or update an Edge (connection).
    """
    PIN_SIZE = 10

    def __init__(self, parent_node, is_output=False):
        super().__init__(0, 0, self.PIN_SIZE, self.PIN_SIZE, parent_node)
        self.parent_node = parent_node
        self.is_output = is_output
        self.dragging_edge = None

        # Pin appearance
        self.setBrush(QBrush(Qt.GlobalColor.darkCyan if self.is_output else Qt.GlobalColor.darkGreen))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)
        self.setZValue(2)

    def centerPos(self):
        """
        Returns the center position of this pin in scene coordinates.
        """
        return self.sceneBoundingRect().center()

    def mousePressEvent(self, event):
        """
        When the user presses the left mouse button on this pin, 
        create a temporary Edge object to represent a new connection being dragged.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            fromEdge = self if self.is_output else None
            toEdge   = None if self.is_output else self
            self.dragging_edge = Edge(source_pin=fromEdge, 
                                      target_pin=toEdge, 
                                      is_temp=True)
            self.scene().addItem(self.dragging_edge)
            self.dragging_edge.updatePath()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        During the drag, update the temporary edge to follow the mouse.
        """
        if self.dragging_edge:
            scene_pos = event.scenePos()
            self.dragging_edge.setDraggingEnd(scene_pos)
            self.dragging_edge.updatePath()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        On mouse release, if released over a compatible pin, finalize the connection.
        """
        if self.dragging_edge:
            scene_pos = event.scenePos()
            # Search nearby items for a compatible pin
            items = self.scene().items(QRectF(scene_pos - QPointF(5, 5),
                                              scene_pos + QPointF(5, 5)))
            target_pin = None
            for it in items:
                if isinstance(it, Pin) and (it.is_output != self.is_output):
                    target_pin = it
                    break

            if target_pin:
                # Output pin -> Input pin
                src_pin = self if self.is_output else target_pin
                dst_pin = target_pin if self.is_output else self
                self.scene().addEdge(src_pin, dst_pin)

            # Remove the temporary edge
            self.scene().removeItem(self.dragging_edge)
            self.dragging_edge = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class Edge(QGraphicsPathItem):
    """
    A bezier-curve style connection (edge) between two Pins.
    If is_temp=True, it represents a temporary edge being dragged.
    """
    def __init__(self, source_pin=None, target_pin=None, is_temp=False):
        super().__init__()
        self.source_pin  = source_pin
        self.target_pin = target_pin
        self.is_temp = is_temp
        self.dragging_end = None

        pen = QPen(Qt.GlobalColor.black, 2)
        self.setPen(pen)
        self.setZValue(1)

    def setDraggingEnd(self, scene_pos: QPointF):
        """
        Set the temporary edge's end point (usually the mouse position).
        """
        self.dragging_end = scene_pos

    def sourcePin(self):
        return self.source_pin

    def targetPin(self):
        return self.target_pin

    def updatePath(self):
        """
        Update the bezier path from the source pin to target pin 
        or (in the case of a temporary edge) to the dragging_end.
        """
        if self.source_pin:
            p1 = self.source_pin.centerPos()
        elif self.target_pin:
            p1 = self.target_pin.centerPos()
        else:
            return

        if self.is_temp:
            # Use dragging_end as the second anchor if it's a temporary edge
            p2 = self.dragging_end if self.dragging_end else p1
        else:
            if self.target_pin:
                p2 = self.target_pin.centerPos()
            else:
                return

        dx = abs(p2.x() - p1.x()) * 0.5
        p1c = QPointF(p1.x() + dx, p1.y())
        p2c = QPointF(p2.x() - dx, p2.y())

        path = QPainterPath(p1)
        path.cubicTo(p1c, p2c, p2)
        self.setPath(path)

    def edgeData(self):
        """
        Return an EdgeData object for this edge. 
        Contains the source/target node IDs.
        """
        s_id = self.source_pin.parent_node.id() if self.source_pin else -1
        t_id = self.target_pin.parent_node.id() if self.target_pin else -1
        return EdgeData(source_node_id=s_id, target_node_id=t_id)


class NodeItem(QGraphicsRectItem):
    """
    A rectangular node that includes:
      - A title
      - A pair of Pins (input, output)
      - CMake configuration info (or any additional info).
    """
    def __init__(self, node_id=0, title="NewNode", cmake_options=None, 
                 project_path="", data: NodeData=None):
        super().__init__(0, 0, 150, 60)

        # Initialize NodeData
        if data is None:
            # If no NodeData was provided, create one
            default_bs = BuildSettings(
                build_dir=os.path.join(os.getcwd(), "build"),
                install_dir=os.path.join(os.getcwd(), "install"),
                build_type="Debug",
                prefix_path=os.path.join(os.getcwd(), "install"),
                toolchain_file="",
                generator="",
            )
            self._data = NodeData(
                node_id=node_id,
                title=title,
                pos_x=0,
                pos_y=0,
                cmake_options=cmake_options if cmake_options else [],
                project_path=project_path,
                build_settings=default_bs,
                code_before_build="",
                code_after_install=""
            )
        else:
            # If NodeData is provided, use it
            self._data = data
            # Restore position
            self.setPos(self._data.pos_x, self._data.pos_y)

        # Make sure children (pins) can receive clicks
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, False)
        # Allow selection, movement, geometry change signals
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # Appearance
        self.setBrush(QBrush(Qt.GlobalColor.lightGray))
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setZValue(0)

        # Title text
        self.text_item = QGraphicsTextItem(self._data.title, self)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.centerTitle()

        # Pins (left input, right output)
        self.input_pin  = Pin(self, is_output=False)
        self.output_pin = Pin(self, is_output=True)
        self.updatePinsPos()

    def centerTitle(self):
        """
        Position the title text in the center of the node rectangle.
        """
        rect = self.rect()
        trect = self.text_item.boundingRect()
        cx = rect.x() + (rect.width() - trect.width()) / 2
        cy = rect.y() + (rect.height() - trect.height()) / 2
        self.text_item.setPos(cx, cy)

    def updateTitle(self, new_title):
        self._data.title = new_title
        self.text_item.setPlainText(new_title)
        self.centerTitle()

    def setCMakeOptions(self, options_list):
        self._data.cmake_options = options_list

    def setProjectPath(self, path_str):
        self._data.project_path = path_str

    def updatePinsPos(self):
        """
        Position the input pin on the left middle side,
        and the output pin on the right middle side.
        """
        rect = self.rect()
        half_size = Pin.PIN_SIZE / 2
        # Input pin on left center
        self.input_pin.setPos(rect.x() - half_size,
                              rect.y() + (rect.height() - Pin.PIN_SIZE) / 2)
        # Output pin on right center
        self.output_pin.setPos(rect.x() + rect.width() - half_size,
                               rect.y() + (rect.height() - Pin.PIN_SIZE) / 2)

    def itemChange(self, change, value):
        """
        When the node moves, update any connected edges and store the new position in NodeData.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.updatePinsPos()
            if self.scene():
                for edge in self.scene().edges:
                    if edge.sourcePin() and edge.sourcePin().parent_node == self:
                        edge.updatePath()
                    if edge.targetPin() and edge.targetPin().parent_node == self:
                        edge.updatePath()

            # Update NodeData pos_x, pos_y
            self._data.pos_x = self.pos().x()
            self._data.pos_y = self.pos().y()

        return super().itemChange(change, value)

    # -- Accessors --
    def id(self):
        return self._data.node_id

    def title(self):
        return self._data.title

    def posX(self):
        return self._data.pos_x

    def posY(self):
        return self._data.pos_y

    def cmakeOptions(self):
        return self._data.cmake_options

    def projectPath(self):
        return self._data.project_path

    def buildSettings(self) -> BuildSettings:
        return self._data.build_settings

    def setBuildSettings(self, bs: BuildSettings):
        self._data.build_settings = bs

    def codeBeforeBuild(self):
        return self._data.code_before_build

    def setCodeBeforeBuild(self, code_str):
        self._data.code_before_build = code_str

    def codeAfterInstall(self):
        return self._data.code_after_install

    def setCodeAfterInstall(self, code_str):
        self._data.code_after_install = code_str

    def nodeData(self) -> NodeData:
        return self._data


class NodeScene(QGraphicsScene):
    """
    A QGraphicsScene that manages:
      - All NodeItem and Edge objects
      - Topological sorting 
      - Project saving/loading (including global config).
    """
    nodeCounter = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 1200, 800)
        self.nodes = []
        self.edges = []
        self.topology_changed_callback = None

    def drawBackground(self, painter, rect):
        """Draw a simple grid as the scene background."""
        super().drawBackground(painter, rect)
        grid_size = 20

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.save()
        painter.setPen(QPen(Qt.GlobalColor.lightGray, 1))

        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += grid_size

        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += grid_size

        painter.restore()

    def setTopologyCallback(self, func):
        """
        Set a callback to be called whenever topology might have changed.
        """
        self.topology_changed_callback = func

    def notifyTopologyChanged(self):
        if self.topology_changed_callback:
            self.topology_changed_callback()

    def addNewNode(self, title, cmake_options, project_path, build_settings=None):
        """
        Create a new NodeItem, place it in the scene, and update topology.
        """
        node_id = NodeScene.nodeCounter
        NodeScene.nodeCounter += 1
        if build_settings is None:
            build_settings = BuildSettings(
                build_dir=os.path.join(os.getcwd(), "build"),
                install_dir=os.path.join(os.getcwd(), "install"),
                build_type="Debug",
                prefix_path=os.path.join(os.getcwd(), "install"),
                toolchain_file="",
                generator="",
            )
        new_node = NodeItem(node_id=node_id,
                            title=title,
                            cmake_options=cmake_options,
                            project_path=project_path,
                            data=None)
        # Override build settings
        new_node.setBuildSettings(build_settings)
        new_node.setPos(100, 100)
        new_node.nodeData().pos_x = 100
        new_node.nodeData().pos_y = 100
        self.addItem(new_node)
        self.nodes.append(new_node)
        self.notifyTopologyChanged()
        return new_node

    def removeNode(self, node_item):
        """
        Remove the specified node and any edges connected to it.
        """
        if node_item in self.nodes:
            edges_to_remove = []
            for e in self.edges:
                if (e.sourcePin() and e.sourcePin().parent_node == node_item) or \
                   (e.targetPin() and e.targetPin().parent_node == node_item):
                    edges_to_remove.append(e)

            for e in edges_to_remove:
                self.removeEdge(e)

            self.removeItem(node_item)
            self.nodes.remove(node_item)
            self.notifyTopologyChanged()

    def addEdge(self, source_pin, target_pin):
        """
        Create an Edge from source_pin to target_pin, add to scene, update path, notify topology.
        """
        # Prevent self-loop and duplicate edges
        if source_pin.parent_node == target_pin.parent_node:
            return
        for e in self.edges:
            if e.sourcePin() == source_pin and e.targetPin() == target_pin:
                return

        edge = Edge(source_pin, target_pin, is_temp=False)
        self.addItem(edge)
        self.edges.append(edge)
        edge.updatePath()
        self.notifyTopologyChanged()

    def removeEdge(self, edge):
        """
        Remove the given edge from the scene.
        """
        if edge in self.edges:
            self.removeItem(edge)
            self.edges.remove(edge)
            self.notifyTopologyChanged()

    def topologicalSort(self):
        """
        Perform a topological sort on the scene's nodes based on edges (output->input).
        Return None if there's a cycle.
        """
        adjacency = {}
        in_degree = {}

        for node in self.nodes:
            adjacency[node] = []
            in_degree[node] = 0

        for edge in self.edges:
            src_node = edge.sourcePin().parent_node
            dst_node = edge.targetPin().parent_node
            adjacency[src_node].append(dst_node)
            in_degree[dst_node] += 1

        queue = deque()
        for n, deg in in_degree.items():
            if deg == 0:
                queue.append(n)

        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for child in adjacency[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) < len(self.nodes):
            # There's a cycle
            return None
        return result

    def saveProjectToJson(self, filepath, start_node_id=None):
        """
        Save this scene to a JSON file.
        Includes:
         - global config (if any)
         - node data
         - edge data
        """
        data = {
            "global": {"start_node_id": start_node_id} if start_node_id is not None else {},
            "nodes": [],
            "edges": []
        }

        # Serialize nodes
        for node in self.nodes:
            data["nodes"].append(asdict(node.nodeData()))

        # Serialize edges
        for edge in self.edges:
            data["edges"].append(asdict(edge.edgeData()))

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def loadProjectFromJson(self, filepath):
        """
        Load the scene (nodes/edges) plus global config from the specified JSON file.
        Returns the global config as a dict.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        global_cfg = data.get("global", {})
        self.clearScene()

        # Update nodeCounter
        NodeScene.nodeCounter = 1
        for nd in data.get("nodes", []):
            node_id = nd["node_id"]
            NodeScene.nodeCounter = max(NodeScene.nodeCounter, node_id + 1)

        node_map = {}
        # Recreate nodes
        for nd in data.get("nodes", []):
            bs_dict = nd.get("build_settings", {})
            bs = BuildSettings(
                build_dir=bs_dict.get("build_dir", os.path.join(os.getcwd(), "build")),
                install_dir=bs_dict.get("install_dir", os.path.join(os.getcwd(), "install")),
                build_type=bs_dict.get("build_type", "Debug"),
                prefix_path=bs_dict.get("prefix_path", os.path.join(os.getcwd(), "install")),
                toolchain_file=bs_dict.get("toolchain_file", ""),
                generator=bs_dict.get("generator", ""),
                c_compiler=bs_dict.get("c_compiler", ""),
                cxx_compiler=bs_dict.get("cxx_compiler", ""),
            )
            node_data = NodeData(
                node_id=nd["node_id"],
                title=nd["title"],
                pos_x=nd["pos_x"],
                pos_y=nd["pos_y"],
                cmake_options=nd.get("cmake_options", []),
                project_path=nd.get("project_path", ""),
                build_settings=bs,
                code_before_build=nd.get("code_before_build", ""),
                code_after_install=nd.get("code_after_install", ""),
            )
            node_item = NodeItem(data=node_data)
            self.addItem(node_item)
            self.nodes.append(node_item)
            node_map[node_item.id()] = node_item

        # Recreate edges
        for ed in data.get("edges", []):
            src_id = ed["source_node_id"]
            dst_id = ed["target_node_id"]
            if src_id in node_map and dst_id in node_map:
                self.addEdge(node_map[src_id].output_pin, node_map[dst_id].input_pin)

        self.notifyTopologyChanged()
        return global_cfg

    def clearScene(self):
        """
        Remove all edges and nodes from the scene.
        """
        for e in self.edges[:]:
            self.removeEdge(e)
        for n in self.nodes[:]:
            self.removeNode(n)
        self.nodes.clear()
        self.edges.clear()

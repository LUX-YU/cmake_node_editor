import os
import json
from collections import deque

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QBrush, QPen, QPainterPath
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem, QGraphicsTextItem

class Pin(QGraphicsRectItem):
    """
    表示节点上的一个“引脚”（input 或 output）。
    通过鼠标拖拽该引脚，可以创建/更新连线 (Edge)。
    """
    PIN_SIZE = 10

    def __init__(self, parent_node, is_output=False):
        super().__init__(0, 0, self.PIN_SIZE, self.PIN_SIZE, parent_node)
        self.parent_node = parent_node
        self.is_output = is_output
        self.dragging_edge = None

        self.setBrush(QBrush(Qt.GlobalColor.darkCyan if self.is_output else Qt.GlobalColor.darkGreen))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)
        self.setZValue(2)

    def centerPos(self):
        br = self.sceneBoundingRect()
        return br.center()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_edge = Edge(
                source_pin=self if self.is_output else None,
                target_pin=None if self.is_output else self,
                is_temp=True
            )
            self.scene().addItem(self.dragging_edge)
            self.dragging_edge.updatePath()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_edge:
            scene_pos = event.scenePos()
            self.dragging_edge.setDraggingEnd(scene_pos)
            self.dragging_edge.updatePath()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging_edge:
            scene_pos = event.scenePos()
            items = self.scene().items(QRectF(scene_pos - QPointF(5, 5),
                                              scene_pos + QPointF(5, 5)))
            target_pin = None
            for it in items:
                if isinstance(it, Pin) and (it.is_output != self.is_output):
                    target_pin = it
                    break
            if target_pin:
                src_pin = self if self.is_output else target_pin
                dst_pin = target_pin if self.is_output else self
                self.scene().addEdge(src_pin, dst_pin)
            self.scene().removeItem(self.dragging_edge)
            self.dragging_edge = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class Edge(QGraphicsPathItem):
    """
    节点之间的连线(贝塞尔曲线)。
    """
    def __init__(self, source_pin=None, target_pin=None, is_temp=False):
        super().__init__()
        self.source_pin = source_pin
        self.target_pin = target_pin
        self.is_temp = is_temp
        self.dragging_end = None

        pen = QPen(Qt.GlobalColor.black, 2)
        self.setPen(pen)
        self.setZValue(1)

    def setDraggingEnd(self, scene_pos: QPointF):
        self.dragging_end = scene_pos

    def updatePath(self):
        if self.source_pin:
            p1 = self.source_pin.centerPos()
        elif self.target_pin:
            p1 = self.target_pin.centerPos()
        else:
            return

        if self.is_temp:
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


class NodeItem(QGraphicsRectItem):
    """
    一个矩形节点：包含标题 + 左右两个引脚(输入/输出) + CMake 配置等信息。
    """
    def __init__(self, node_id, title="NewNode", cmake_options=None, project_path=""):
        super().__init__(0, 0, 150, 60)
        self.node_id = node_id
        self.title = title
        self.cmake_option_list = cmake_options if cmake_options else []
        self.project_path = project_path

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, False)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        self.setBrush(QBrush(Qt.GlobalColor.lightGray))
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setZValue(0)

        # 文本标题
        self.text_item = QGraphicsTextItem(self.title, self)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.centerTitle()

        # 引脚：左(input)、右(output)
        self.input_pin = Pin(self, is_output=False)
        self.output_pin = Pin(self, is_output=True)
        self.updatePinsPos()

    def centerTitle(self):
        rect = self.rect()
        trect = self.text_item.boundingRect()
        cx = rect.x() + (rect.width() - trect.width()) / 2
        cy = rect.y() + (rect.height() - trect.height()) / 2
        self.text_item.setPos(cx, cy)

    def updateTitle(self, new_title):
        self.title = new_title
        self.text_item.setPlainText(new_title)
        self.centerTitle()

    def setCMakeOptions(self, options_list):
        self.cmake_option_list = options_list

    def setProjectPath(self, path_str):
        self.project_path = path_str

    def updatePinsPos(self):
        rect = self.rect()
        self.input_pin.setPos(rect.x() - Pin.PIN_SIZE/2,
                              rect.y() + (rect.height()-Pin.PIN_SIZE)/2)
        self.output_pin.setPos(rect.x() + rect.width() - Pin.PIN_SIZE/2,
                               rect.y() + (rect.height()-Pin.PIN_SIZE)/2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.updatePinsPos()
            if self.scene():
                for edge in self.scene().edges:
                    if edge.source_pin and edge.source_pin.parent_node == self:
                        edge.updatePath()
                    if edge.target_pin and edge.target_pin.parent_node == self:
                        edge.updatePath()
        return super().itemChange(change, value)


class NodeScene(QGraphicsScene):
    """
    场景，管理所有节点、连线，以及拓扑排序、保存加载等。
    """
    nodeCounter = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 1200, 800)
        self.nodes = []
        self.edges = []
        self.topology_changed_callback = None

    def setTopologyCallback(self, func):
        self.topology_changed_callback = func

    def notifyTopologyChanged(self):
        if self.topology_changed_callback:
            self.topology_changed_callback()

    def addNewNode(self, title, cmake_options, project_path):
        node_id = NodeScene.nodeCounter
        NodeScene.nodeCounter += 1
        new_node = NodeItem(node_id, title, cmake_options, project_path)
        new_node.setPos(100, 100)
        self.addItem(new_node)
        self.nodes.append(new_node)
        self.notifyTopologyChanged()
        return new_node

    def removeNode(self, node_item):
        if node_item in self.nodes:
            edges_to_remove = []
            for e in self.edges:
                if (e.source_pin and e.source_pin.parent_node == node_item) or \
                   (e.target_pin and e.target_pin.parent_node == node_item):
                    edges_to_remove.append(e)
            for e in edges_to_remove:
                self.removeEdge(e)
            self.removeItem(node_item)
            self.nodes.remove(node_item)
            self.notifyTopologyChanged()

    def addEdge(self, source_pin, target_pin):
        edge = Edge(source_pin, target_pin, is_temp=False)
        self.addItem(edge)
        self.edges.append(edge)
        edge.updatePath()
        self.notifyTopologyChanged()

    def removeEdge(self, edge):
        if edge in self.edges:
            self.removeItem(edge)
            self.edges.remove(edge)
            self.notifyTopologyChanged()

    def topologicalSort(self):
        adjacency = {}
        in_degree = {}
        for node in self.nodes:
            adjacency[node] = []
            in_degree[node] = 0

        for edge in self.edges:
            src_node = edge.source_pin.parent_node
            dst_node = edge.target_pin.parent_node
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
            return None
        return result

    # ------------------- 修改：支持同时保存全局配置 -------------------
    def saveProjectToJson(self, filepath, global_config=None):
        """
        新增可选参数 global_config，用于同时保存全局构建配置。
        """
        data = {
            "global": global_config if global_config else {},  # 存储全局配置
            "nodes": [],
            "edges": []
        }

        for node in self.nodes:
            x = node.pos().x()
            y = node.pos().y()
            data["nodes"].append({
                "node_id": node.node_id,
                "title": node.title,
                "pos_x": x,
                "pos_y": y,
                "cmake_options": node.cmake_option_list,
                "project_path": node.project_path
            })

        for edge in self.edges:
            src_id = edge.source_pin.parent_node.node_id
            dst_id = edge.target_pin.parent_node.node_id
            data["edges"].append({
                "source_node_id": src_id,
                "target_node_id": dst_id
            })

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def loadProjectFromJson(self, filepath):
        """
        返回一个 dict, 表示从文件中读取到的 global_config（全局配置）.
        同时重建本场景的 nodes/edges.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 读取 global_config
        global_cfg = data.get("global", {})

        self.clearScene()

        NodeScene.nodeCounter = 1
        for nd in data.get("nodes", []):
            node_id = nd["node_id"]
            NodeScene.nodeCounter = max(NodeScene.nodeCounter, node_id + 1)

        node_map = {}
        for nd in data.get("nodes", []):
            node_id = nd["node_id"]
            title = nd["title"]
            x = nd["pos_x"]
            y = nd["pos_y"]
            cmake_opts = nd.get("cmake_options", [])
            project_path = nd.get("project_path", "")
            node_item = NodeItem(node_id, title, cmake_opts, project_path)
            node_item.setPos(x, y)
            self.addItem(node_item)
            self.nodes.append(node_item)
            node_map[node_id] = node_item

        for ed in data.get("edges", []):
            src_id = ed["source_node_id"]
            dst_id = ed["target_node_id"]
            if src_id in node_map and dst_id in node_map:
                self.addEdge(node_map[src_id].output_pin, node_map[dst_id].input_pin)

        self.notifyTopologyChanged()

        # 返回 global_cfg 给外部
        return global_cfg

    def clearScene(self):
        for e in self.edges[:]:
            self.removeEdge(e)
        for n in self.nodes[:]:
            self.removeNode(n)
        self.nodes.clear()
        self.edges.clear()

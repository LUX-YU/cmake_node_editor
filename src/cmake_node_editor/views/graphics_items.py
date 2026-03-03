"""
Graphics items: Pin, Edge, and NodeItem.

These are the core visual elements rendered on the :class:`NodeScene`.
They were originally defined in the monolithic ``node_scene.py`` and
have been extracted here for better separation of concerns.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QBrush, QPen, QPainterPath, QColor, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsPathItem,
    QGraphicsItem, QGraphicsTextItem,
)

from ..models.data_classes import NodeData, EdgeData, BuildSettings, CustomCommands
from ..constants import (
    NODE_WIDTH, NODE_HEIGHT, PIN_SIZE,
    DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE,
)


class Pin(QGraphicsRectItem):
    """
    Connection endpoint on a node (input or output).

    Dragging a pin creates a temporary :class:`Edge` that the user can
    drop onto a compatible pin on another node.
    """

    def __init__(self, parent_node: "NodeItem", is_output: bool = False):
        super().__init__(0, 0, PIN_SIZE, PIN_SIZE, parent_node)
        self.parent_node = parent_node
        self.is_output = is_output
        self.dragging_edge: Edge | None = None

        self.setBrush(QBrush(Qt.GlobalColor.darkCyan if self.is_output else Qt.GlobalColor.darkGreen))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setZValue(2)

    def centerPos(self) -> QPointF:
        return self.sceneBoundingRect().center()

    # -- Mouse interaction for edge creation --

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            from_pin = self if self.is_output else None
            to_pin = None if self.is_output else self
            self.dragging_edge = Edge(source_pin=from_pin, target_pin=to_pin, is_temp=True)
            self.scene().addItem(self.dragging_edge)
            self.dragging_edge.updatePath()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging_edge:
            self.dragging_edge.setDraggingEnd(event.scenePos())
            self.dragging_edge.updatePath()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging_edge:
            scene_pos = event.scenePos()
            items = self.scene().items(
                QRectF(scene_pos - QPointF(5, 5), scene_pos + QPointF(5, 5))
            )
            target_pin = None
            for it in items:
                if isinstance(it, Pin) and it.is_output != self.is_output:
                    target_pin = it
                    break

            if target_pin:
                src_pin = self if self.is_output else target_pin
                dst_pin = target_pin if self.is_output else self
                scene = self.scene()
                ctx = getattr(scene, 'context', None)
                if ctx:
                    ctx.undo_add_edge(src_pin, dst_pin)
                else:
                    scene.addEdge(src_pin, dst_pin)

            self.scene().removeItem(self.dragging_edge)
            self.dragging_edge = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class Edge(QGraphicsPathItem):
    """Bezier-curve connection between two :class:`Pin` instances."""

    def __init__(self, source_pin: Pin | None = None,
                 target_pin: Pin | None = None, is_temp: bool = False):
        super().__init__()
        self.source_pin = source_pin
        self.target_pin = target_pin
        self.is_temp = is_temp
        self.dragging_end: QPointF | None = None

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(1)
        self.updateColor()

    ARROW_SIZE = 8  # pixels

    def boundingRect(self):
        """Expand the default path bounding rect to include the arrowhead."""
        base = super().boundingRect()
        margin = self.ARROW_SIZE + self.pen().widthF()
        return base.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # Draw arrowhead at the target end
        path = self.path()
        if path.isEmpty():
            return
        percent = path.percentAtLength(path.length())
        end_pt = path.pointAtPercent(percent)
        # Get a point slightly before the end to compute direction
        t_back = path.percentAtLength(max(0, path.length() - 1))
        pre_pt = path.pointAtPercent(t_back)
        dx = end_pt.x() - pre_pt.x()
        dy = end_pt.y() - pre_pt.y()
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return
        # Unit direction vector
        ux, uy = dx / length, dy / length
        # Perpendicular
        px, py = -uy, ux
        s = self.ARROW_SIZE
        arrow = QPolygonF([
            end_pt,
            QPointF(end_pt.x() - s * ux + s * 0.5 * px,
                    end_pt.y() - s * uy + s * 0.5 * py),
            QPointF(end_pt.x() - s * ux - s * 0.5 * px,
                    end_pt.y() - s * uy - s * 0.5 * py),
        ])
        painter.setBrush(self.pen().color())
        painter.drawPolygon(arrow)

    def updateColor(self):
        scene = self.scene()
        base = scene.link_color if scene else QColor(Qt.GlobalColor.black)
        if self.isSelected():
            inv = QColor(255 - base.red(), 255 - base.green(), 255 - base.blue())
            pen = QPen(inv, 3)
        else:
            pen = QPen(base, 2)
        self.setPen(pen)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.updateColor()
        return super().itemChange(change, value)

    def setDraggingEnd(self, scene_pos: QPointF):
        self.dragging_end = scene_pos

    def sourcePin(self) -> Pin | None:
        return self.source_pin

    def targetPin(self) -> Pin | None:
        return self.target_pin

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

    def edgeData(self) -> EdgeData:
        s_id = self.source_pin.parent_node.id() if self.source_pin else -1
        t_id = self.target_pin.parent_node.id() if self.target_pin else -1
        return EdgeData(source_node_id=s_id, target_node_id=t_id)


class NodeItem(QGraphicsRectItem):
    """
    Visual representation of a CMake project node.

    Contains a title label, input/output :class:`Pin` instances, and a
    :class:`NodeData` payload with all CMake configuration.
    """

    def __init__(self, node_id: int = 0, title: str = "NewNode",
                 cmake_options: list[str] | None = None,
                 project_path: str = "",
                 data: NodeData | None = None):
        super().__init__(0, 0, NODE_WIDTH, NODE_HEIGHT)

        if data is None:
            default_bs = BuildSettings(
                build_dir=DEFAULT_BUILD_DIR,
                install_dir=DEFAULT_INSTALL_DIR,
                build_type=DEFAULT_BUILD_TYPE,
                prefix_path=DEFAULT_INSTALL_DIR,
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
                code_after_install="",
            )
        else:
            self._data = data
            self.setPos(self._data.pos_x, self._data.pos_y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, False)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setBrush(QBrush(Qt.GlobalColor.lightGray))
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setZValue(0)

        self.text_item = QGraphicsTextItem(self._data.title, self)
        self.text_item.setDefaultTextColor(Qt.GlobalColor.black)
        self.centerTitle()

        self.input_pin = Pin(self, is_output=False)
        self.output_pin = Pin(self, is_output=True)
        self.updatePinsPos()

    # -- Events --

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.scene():
            ctx = getattr(self.scene(), 'context', None)
            if ctx:
                ctx.nodeDoubleClicked.emit(self)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.updatePinsPos()
            if self.scene():
                for edge in self.scene().edges:
                    if edge.sourcePin() and edge.sourcePin().parent_node == self:
                        edge.updatePath()
                    if edge.targetPin() and edge.targetPin().parent_node == self:
                        edge.updatePath()
            self._data.pos_x = self.pos().x()
            self._data.pos_y = self.pos().y()
        return super().itemChange(change, value)

    # -- Layout helpers --

    def centerTitle(self):
        rect = self.rect()
        trect = self.text_item.boundingRect()
        cx = rect.x() + (rect.width() - trect.width()) / 2
        cy = rect.y() + (rect.height() - trect.height()) / 2
        self.text_item.setPos(cx, cy)

    def updatePinsPos(self):
        rect = self.rect()
        half = PIN_SIZE / 2
        self.input_pin.setPos(rect.x() - half,
                              rect.y() + (rect.height() - PIN_SIZE) / 2)
        self.output_pin.setPos(rect.x() + rect.width() - half,
                               rect.y() + (rect.height() - PIN_SIZE) / 2)

    # -- Mutators --

    def updateTitle(self, new_title: str):
        self._data.title = new_title
        self.text_item.setPlainText(new_title)
        self.centerTitle()

    def setCMakeOptions(self, options_list: list[str]):
        self._data.cmake_options = options_list

    def setProjectPath(self, path_str: str):
        self._data.project_path = path_str

    def setBuildSettings(self, bs: BuildSettings):
        self._data.build_settings = bs

    def setCodeBeforeBuild(self, code_str: str):
        self._data.code_before_build = code_str

    def setCodeAfterInstall(self, code_str: str):
        self._data.code_after_install = code_str

    def setBuildSystem(self, build_system: str):
        self._data.build_system = build_system

    def setCustomCommands(self, cc: CustomCommands | None):
        self._data.custom_commands = cc

    # -- Accessors --

    def id(self) -> int:
        return self._data.node_id

    def title(self) -> str:
        return self._data.title

    def posX(self) -> float:
        return self._data.pos_x

    def posY(self) -> float:
        return self._data.pos_y

    def cmakeOptions(self) -> list[str]:
        return self._data.cmake_options

    def projectPath(self) -> str:
        return self._data.project_path

    def buildSettings(self) -> BuildSettings:
        return self._data.build_settings

    def codeBeforeBuild(self) -> str:
        return self._data.code_before_build

    def codeAfterInstall(self) -> str:
        return self._data.code_after_install

    def buildSystem(self) -> str:
        return self._data.build_system

    def customCommands(self) -> CustomCommands | None:
        return self._data.custom_commands

    def nodeData(self) -> NodeData:
        return self._data

"""
Graphics items: Pin, Edge, and NodeItem.

Cyberpunk dark theme — neon glow pins, gradient nodes, multi-pass glow edges.
"""

from __future__ import annotations

import math
import os

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QBrush, QPen, QPainterPath, QColor, QPolygonF,
    QLinearGradient, QFont,
)
from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsPathItem,
    QGraphicsItem, QGraphicsTextItem,
)

from ..models.data_classes import NodeData, EdgeData, BuildSettings, CustomCommands
from ..constants import (
    NODE_WIDTH, NODE_HEIGHT, PIN_SIZE,
    NODE_CORNER_RADIUS, NODE_HEADER_HEIGHT, NODE_GLOW_MARGIN,
    DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE,
)
from ..theme import (
    PIN_IN, PIN_OUT,
    EDGE_NORMAL, EDGE_SELECTED, EDGE_TEMP,
    NODE_BG_TOP, NODE_BG_BOT, NODE_HDR_TOP, NODE_HDR_BOT,
    NODE_BORDER, NODE_BORDER_SEL, NODE_ACCENT, NODE_ACCENT_SEL,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    ACCENT_CYAN, ACCENT_BLUE,
)


class Pin(QGraphicsRectItem):
    """
    Circular neon connector on a node (input or output).

    Dragging a pin creates a temporary :class:`Edge` that the user can
    drop onto a compatible pin on another node.
    """

    _GLOW = 5  # extra paint area around the pin for glow

    def __init__(self, parent_node: "NodeItem", is_output: bool = False):
        super().__init__(0, 0, PIN_SIZE, PIN_SIZE, parent_node)
        self.parent_node = parent_node
        self.is_output = is_output
        self.dragging_edge: Edge | None = None

        # invisible rect — we draw everything in paint()
        self.setBrush(QBrush())
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setZValue(3)

    def boundingRect(self) -> QRectF:
        g = self._GLOW
        return QRectF(-g, -g, PIN_SIZE + 2 * g, PIN_SIZE + 2 * g)

    def paint(self, painter, option, widget=None):
        base = PIN_OUT if self.is_output else PIN_IN
        pin_rect = QRectF(0, 0, PIN_SIZE, PIN_SIZE)

        painter.setRenderHint(painter.renderHints().Antialiasing, True)

        # -- outer glow rings --
        for extra, alpha in ((8, 0.12), (4, 0.25)):
            glow = QColor(base)
            glow.setAlphaF(alpha)
            painter.setPen(QPen(glow, extra))
            painter.setBrush(QBrush())
            painter.drawEllipse(pin_rect)

        # -- dark filled body --
        painter.setPen(QPen(base, 1.5))
        dark = QColor("#0a1020")
        painter.setBrush(QBrush(dark))
        painter.drawEllipse(pin_rect)

        # -- bright inner dot --
        inner = pin_rect.adjusted(3, 3, -3, -3)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(base))
        painter.drawEllipse(inner)

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
    """Neon-glow bezier connection between two :class:`Pin` instances."""

    ARROW_SIZE = 9   # pixels
    _GLOW_W    = 12  # outermost glow pen width (for bounding rect margin)

    def __init__(self, source_pin: Pin | None = None,
                 target_pin: Pin | None = None, is_temp: bool = False):
        super().__init__()
        self.source_pin = source_pin
        self.target_pin = target_pin
        self.is_temp = is_temp
        self.dragging_end: QPointF | None = None

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(1)
        # set a placeholder pen for bounding-rect queries before first paint
        self.setPen(QPen(EDGE_NORMAL, 2))

    def boundingRect(self):
        base = super().boundingRect()
        margin = self.ARROW_SIZE + self._GLOW_W
        return base.adjusted(-margin, -margin, margin, margin)

    def _edge_color(self) -> QColor:
        if self.is_temp:
            return EDGE_TEMP
        scene = self.scene()
        base = scene.link_color if scene else EDGE_NORMAL
        return EDGE_SELECTED if self.isSelected() else base

    def paint(self, painter, option, widget=None):
        path = self.path()
        if path.isEmpty():
            return

        base = self._edge_color()
        painter.setBrush(QBrush())
        painter.setRenderHint(painter.renderHints().Antialiasing, True)

        # multi-pass glow effect
        for width, alpha in ((12, 0.07), (6, 0.18), (3, 0.40), (1.5, 1.0)):
            c = QColor(base)
            c.setAlphaF(alpha)
            painter.setPen(QPen(c, width))
            painter.drawPath(path)

        # -- arrowhead --
        path_len = path.length()
        if path_len < 1.0:
            return
        end_pt  = path.pointAtPercent(path.percentAtLength(path_len))
        t_back  = path.percentAtLength(max(0.0, path_len - 2.0))
        pre_pt  = path.pointAtPercent(t_back)
        dx = end_pt.x() - pre_pt.x()
        dy = end_pt.y() - pre_pt.y()
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux
        s = self.ARROW_SIZE
        arrow = QPolygonF([
            end_pt,
            QPointF(end_pt.x() - s * ux + s * 0.45 * px,
                    end_pt.y() - s * uy + s * 0.45 * py),
            QPointF(end_pt.x() - s * ux - s * 0.45 * px,
                    end_pt.y() - s * uy - s * 0.45 * py),
        ])
        # draw arrow glow
        glow_a = QColor(base); glow_a.setAlphaF(0.30)
        painter.setPen(QPen(glow_a, 3))
        painter.setBrush(glow_a)
        painter.drawPolygon(arrow)
        # solid arrow core
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(base))
        painter.drawPolygon(arrow)

    def updateColor(self):
        # keep the stored pen width consistent; actual color is applied in paint()
        self.setPen(QPen(self._edge_color(), 2))
        self.update()

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

    Dark-panel design: gradient body, coloured header strip,
    neon border glow on selection.
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

        # invisible rect — drawn entirely via paint()
        self.setBrush(QBrush())
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(0)

        # Keep a hidden QGraphicsTextItem so that centerTitle() / updateTitle()
        # keep working (text measurement), but we draw the actual text manually
        # in paint() for drop-shadow support.
        self.text_item = QGraphicsTextItem(self._data.title, self)
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        self.text_item.setFont(title_font)
        self.text_item.setDefaultTextColor(QColor(0, 0, 0, 0))  # fully transparent
        self.centerTitle()

        self.input_pin = Pin(self, is_output=False)
        self.output_pin = Pin(self, is_output=True)
        self.updatePinsPos()

    # -- Custom drawing --

    def boundingRect(self) -> QRectF:
        g = NODE_GLOW_MARGIN
        return self.rect().adjusted(-g, -g, g, g)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self.rect(), NODE_CORNER_RADIUS, NODE_CORNER_RADIUS)
        return path

    def paint(self, painter, option, widget=None):
        rect   = self.rect()
        r      = NODE_CORNER_RADIUS
        is_sel = self.isSelected()

        painter.setRenderHint(painter.renderHints().Antialiasing, True)

        node_path = QPainterPath()
        node_path.addRoundedRect(rect, r, r)

        # ── selection glow ──
        if is_sel:
            for gw, ga in ((18, 0.06), (10, 0.15), (4, 0.35)):
                gc = QColor(NODE_BORDER_SEL)
                gc.setAlphaF(ga)
                painter.setPen(QPen(gc, gw))
                painter.setBrush(QBrush())
                painter.drawPath(node_path)

        # ── body gradient ──
        body_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        body_grad.setColorAt(0.0, NODE_BG_TOP)
        body_grad.setColorAt(1.0, NODE_BG_BOT)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(body_grad))
        painter.drawPath(node_path)

        # ── header strip (clipped to top) ──
        painter.save()
        painter.setClipRect(QRectF(rect.x(), rect.y(), rect.width(), NODE_HEADER_HEIGHT))
        hdr_path = QPainterPath()
        hdr_path.addRoundedRect(rect, r, r)
        hdr_grad = QLinearGradient(
            QPointF(rect.x(), rect.y()),
            QPointF(rect.x(), rect.y() + NODE_HEADER_HEIGHT)
        )
        hdr_grad.setColorAt(0.0, NODE_HDR_TOP)
        hdr_grad.setColorAt(1.0, NODE_HDR_BOT)
        painter.setBrush(QBrush(hdr_grad))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawPath(hdr_path)
        painter.restore()

        # ── header bottom accent line ──
        accent = NODE_ACCENT_SEL if is_sel else NODE_ACCENT
        ac = QColor(accent)
        ac.setAlphaF(0.85 if is_sel else 0.55)
        dy = rect.y() + NODE_HEADER_HEIGHT
        painter.setPen(QPen(ac, 1))
        painter.drawLine(
            QPointF(rect.x() + r, dy),
            QPointF(rect.x() + rect.width() - r, dy),
        )

        # ── body info text (build system + short path) ──
        bs = self._data.build_system or "cmake"
        raw_path = self._data.project_path or ""
        short_path = os.path.basename(os.path.normpath(raw_path)) if raw_path else "\u2014"
        info_text = f"{bs}  \u00b7  {short_path}"
        body_rect = QRectF(
            rect.x() + 6,
            rect.y() + NODE_HEADER_HEIGHT + 2,
            rect.width() - 12,
            rect.height() - NODE_HEADER_HEIGHT - 4,
        )
        info_font = QFont("Segoe UI", 8)
        painter.setFont(info_font)
        painter.setPen(QPen(QColor(TEXT_SECONDARY)))
        painter.drawText(body_rect, Qt.AlignmentFlag.AlignCenter, info_text)

        # ── node border ──
        border_col = NODE_BORDER_SEL if is_sel else NODE_BORDER
        border_w   = 1.8 if is_sel else 1.2
        painter.setPen(QPen(border_col, border_w))
        painter.setBrush(QBrush())
        painter.drawPath(node_path)

        # ── title text with drop-shadow ──
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        painter.setFont(title_font)
        trect = self.text_item.boundingRect()
        tx = rect.x() + (rect.width() - trect.width()) / 2
        ty = rect.y() + (NODE_HEADER_HEIGHT - trect.height()) / 2
        title_rect = QRectF(tx, ty, trect.width(), trect.height())
        # shadow pass
        shadow_rect = title_rect.translated(1, 1)
        painter.setPen(QPen(QColor(0, 0, 0, 140)))
        painter.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, self._data.title)
        # main text
        painter.setPen(QPen(QColor(TEXT_PRIMARY)))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self._data.title)

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
        cy = rect.y() + (NODE_HEADER_HEIGHT - trect.height()) / 2
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
        self.update()

    def setBuildSettings(self, bs: BuildSettings):
        self._data.build_settings = bs

    def setCodeBeforeBuild(self, code_str: str):
        self._data.code_before_build = code_str

    def setCodeAfterInstall(self, code_str: str):
        self._data.code_after_install = code_str

    def setBuildSystem(self, build_system: str):
        self._data.build_system = build_system
        self.update()

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

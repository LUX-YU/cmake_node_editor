"""
Pure graph model — nodes, edges, topological sort.

This module holds the graph data structure **without** any Qt dependency
beyond the data it stores. It can thus be unit-tested without a running
``QApplication``.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF

from ..models.data_classes import NodeData, EdgeData, BuildSettings
from ..constants import (
    DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE,
    NODE_AUTO_OFFSET_X, NODE_AUTO_OFFSET_Y,
    NODE_INITIAL_X, NODE_INITIAL_Y,
)

if TYPE_CHECKING:
    from ..views.graphics_items import NodeItem, Edge, Pin


class GraphModel:
    """
    In-memory graph of :class:`NodeItem` and :class:`Edge` objects.

    Provides CRUD operations, topological sorting (Kahn's algorithm) and
    an auto-incrementing node-ID counter.  The actual Qt scene adds / removes
    ``QGraphicsItem`` instances; this model only tracks the logical structure.
    """

    def __init__(self):
        self.node_counter: int = 1
        self.nodes: list[NodeItem] = []
        self.edges: list[Edge] = []
        self.next_node_pos = QPointF(NODE_INITIAL_X, NODE_INITIAL_Y)
        self.topology_changed_callback = None

    # ------------------------------------------------------------------
    # Topology callback
    # ------------------------------------------------------------------

    def setTopologyCallback(self, func):
        self.topology_changed_callback = func

    def notifyTopologyChanged(self):
        if self.topology_changed_callback:
            self.topology_changed_callback()

    # ------------------------------------------------------------------
    # Node helpers
    # ------------------------------------------------------------------

    def next_id(self) -> int:
        nid = self.node_counter
        self.node_counter += 1
        return nid

    def advance_node_pos(self) -> QPointF:
        """Return the current auto-position and advance for the next call."""
        pos = QPointF(self.next_node_pos)
        self.next_node_pos += QPointF(NODE_AUTO_OFFSET_X, NODE_AUTO_OFFSET_Y)
        return pos

    def default_build_settings(self) -> BuildSettings:
        return BuildSettings(
            build_dir=DEFAULT_BUILD_DIR,
            install_dir=DEFAULT_INSTALL_DIR,
            build_type=DEFAULT_BUILD_TYPE,
            prefix_path=DEFAULT_INSTALL_DIR,
            toolchain_file="",
            generator="",
        )

    # ------------------------------------------------------------------
    # Edge helpers
    # ------------------------------------------------------------------

    def has_edge(self, source_pin: "Pin", target_pin: "Pin") -> bool:
        for e in self.edges:
            if e.sourcePin() == source_pin and e.targetPin() == target_pin:
                return True
        return False

    def is_self_loop(self, source_pin: "Pin", target_pin: "Pin") -> bool:
        return source_pin.parent_node is target_pin.parent_node

    # ------------------------------------------------------------------
    # Topological sort
    # ------------------------------------------------------------------

    def topologicalSort(self) -> list["NodeItem"] | None:
        """Kahn's algorithm. Returns *None* on cycle detection."""
        adjacency: dict[NodeItem, list[NodeItem]] = {}
        in_degree: dict[NodeItem, int] = {}

        for node in self.nodes:
            adjacency[node] = []
            in_degree[node] = 0

        for edge in self.edges:
            src_node = edge.sourcePin().parent_node
            dst_node = edge.targetPin().parent_node
            adjacency[src_node].append(dst_node)
            in_degree[dst_node] += 1

        queue = deque(n for n, deg in in_degree.items() if deg == 0)

        result: list[NodeItem] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for child in adjacency[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return result if len(result) == len(self.nodes) else None

"""
JSON serialization / deserialization for node-editor projects.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING

from ..models.data_classes import NodeData, BuildSettings
from ..constants import DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE

if TYPE_CHECKING:
    from ..views.graphics_items import NodeItem, Edge


def save_project(filepath: str, nodes: list["NodeItem"], edges: list["Edge"],
                 start_node_id: int | None = None) -> str | None:
    """Persist the current graph to a JSON file.

    Returns *None* on success or an error message string on failure.
    """
    data = {
        "global": {"start_node_id": start_node_id} if start_node_id is not None else {},
        "nodes": [asdict(node.nodeData()) for node in nodes],
        "edges": [asdict(edge.edgeData()) for edge in edges],
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except OSError as e:
        return f"Failed to save project: {e}"
    return None


def load_project(filepath: str) -> tuple[dict, list[NodeData], list[dict]]:
    """
    Read a project JSON and return ``(global_cfg, node_data_list, edge_dicts)``.

    The caller is responsible for creating actual ``NodeItem`` / ``Edge``
    instances and adding them to the scene.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    global_cfg = data.get("global", {})

    node_data_list: list[NodeData] = []
    for nd in data.get("nodes", []):
        bs_dict = nd.get("build_settings", {})
        bs = BuildSettings(
            build_dir=bs_dict.get("build_dir", DEFAULT_BUILD_DIR),
            install_dir=bs_dict.get("install_dir", DEFAULT_INSTALL_DIR),
            build_type=bs_dict.get("build_type", DEFAULT_BUILD_TYPE),
            prefix_path=bs_dict.get("prefix_path", DEFAULT_INSTALL_DIR),
            toolchain_file=bs_dict.get("toolchain_file", ""),
            generator=bs_dict.get("generator", ""),
            c_compiler=bs_dict.get("c_compiler", ""),
            cxx_compiler=bs_dict.get("cxx_compiler", ""),
        )
        node_data_list.append(NodeData(
            node_id=nd["node_id"],
            title=nd["title"],
            pos_x=nd["pos_x"],
            pos_y=nd["pos_y"],
            cmake_options=nd.get("cmake_options", []),
            project_path=nd.get("project_path", ""),
            build_settings=bs,
            code_before_build=nd.get("code_before_build", ""),
            code_after_install=nd.get("code_after_install", ""),
        ))

    edge_dicts = data.get("edges", [])
    return global_cfg, node_data_list, edge_dicts

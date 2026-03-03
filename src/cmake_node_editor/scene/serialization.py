"""
JSON serialization / deserialization for node-editor projects.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING

from ..models.data_classes import NodeData, BuildSettings, CustomCommands
from ..constants import DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE

if TYPE_CHECKING:
    from ..views.graphics_items import NodeItem, Edge


def save_project(
    filepath: str,
    nodes: list["NodeItem"],
    edges: list["Edge"],
    start_node_id: int | None = None,
    global_build_type: str | None = None,
) -> str | None:
    """Persist the current graph to a JSON file.

    Returns *None* on success or an error message string on failure.
    """
    global_section: dict = {}
    if start_node_id is not None:
        global_section["start_node_id"] = start_node_id
    if global_build_type:
        global_section["build_type"] = global_build_type
    data = {
        "global": global_section,
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
        # Build system (defaults to "cmake" for old project files)
        build_system = nd.get("build_system", "cmake")
        cc_dict = nd.get("custom_commands", None)
        custom_commands = CustomCommands(**cc_dict) if cc_dict else None

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
            build_system=build_system,
            custom_commands=custom_commands,
        ))

    edge_dicts = data.get("edges", [])
    return global_cfg, node_data_list, edge_dicts

"""
JSON serialization / deserialization for node-editor projects.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING

from ..models.data_classes import NodeData, BuildSettings, CustomCommands
from ..constants import DEFAULT_BUILD_DIR, DEFAULT_INSTALL_DIR, DEFAULT_BUILD_TYPE, SAVE_FORMAT_VERSION

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
        "version": SAVE_FORMAT_VERSION,
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

    # -- Migration --
    file_version = data.get("version", 1)
    if file_version < SAVE_FORMAT_VERSION:
        data = _migrate(data, file_version)
        global_cfg = data.get("global", {})
        global_cfg["_migrated_from"] = file_version

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


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def _migrate(data: dict, from_version: int) -> dict:
    """Apply all required migrations from *from_version* up to the current version.

    Each step is a pure function that takes and returns the raw JSON dict.
    """
    import copy
    data = copy.deepcopy(data)
    if from_version < 2:
        data = _migrate_v1_to_v2(data)
    # Future: if from_version < 3: data = _migrate_v2_to_v3(data)
    return data


def _migrate_v1_to_v2(data: dict) -> dict:
    """v1 → v2: ``build_dir`` paths gain an explicit ``{project_name}`` segment.

    In v1 the application always appended the node title to the build
    directory at runtime.  In v2 this is expressed explicitly in the
    path template so users can see and customise it.  Migration appends
    ``/{project_name}`` to any ``build_dir`` value that does not already
    contain ``{project_name}``.
    """
    for node in data.get("nodes", []):
        bs = node.get("build_settings", {})
        build_dir: str = bs.get("build_dir", "")
        if "{project_name}" not in build_dir:
            bs["build_dir"] = build_dir.rstrip("/").rstrip("\\") + "/{project_name}"
    return data

"""
CMake command builder service.

Knows how to produce :class:`ProjectCommands` (configure / build / install
command sequences) from a topologically sorted list of node-like objects.

Any object that exposes ``id()``, ``title()``, ``projectPath()``,
``buildSettings()``, ``cmakeOptions()``, ``codeBeforeBuild()``,
``codeAfterInstall()`` and ``nodeData()`` is accepted (duck typing).
This allows both :class:`NodeItem` (GUI) and :class:`NodeProxy` (CLI) to
be used interchangeably.
"""

from __future__ import annotations

import multiprocessing
import os
import re

from ..models.data_classes import (
    ProjectCommands, NodeCommands, CommandData, NodeData, BuildSettings,
)


def _sanitize_name(name: str) -> str:
    """Remove characters unsafe for filesystem paths."""
    return re.sub(r'[^\w\-.]', '_', name)


class NodeProxy:
    """
    Lightweight adapter that wraps a :class:`NodeData` dataclass and
    exposes the same read-only interface that :func:`build_project_commands`
    expects.  Used by the headless CLI builder.
    """

    def __init__(self, data: NodeData):
        self._data = data

    def id(self) -> int:
        return self._data.node_id

    def title(self) -> str:
        return self._data.title

    def projectPath(self) -> str:
        return self._data.project_path

    def buildSettings(self) -> BuildSettings:
        return self._data.build_settings

    def cmakeOptions(self) -> list[str]:
        return self._data.cmake_options

    def codeBeforeBuild(self) -> str:
        return self._data.code_before_build

    def codeAfterInstall(self) -> str:
        return self._data.code_after_install

    def nodeData(self) -> NodeData:
        return self._data


def _sanitize_name(name: str) -> str:
    """Remove characters unsafe for filesystem paths."""
    return re.sub(r'[^\w\-.]', '_', name)


def build_project_commands(
    sorted_nodes,
    *,
    stage: str = "build",
    start_index: int = 0,
    end_index: int | None = None,
    start_node_id: int | None = None,
    only_first: bool = False,
) -> ProjectCommands | str:
    """
    Assemble :class:`ProjectCommands` for the given *stage*.

    Parameters
    ----------
    sorted_nodes : list[NodeItem]
        Already topologically-sorted node list.
    stage : str
        ``"configure"``, ``"build"``, ``"install"`` or ``"all"``.
    start_index / end_index : int
        Slice boundaries within *sorted_nodes*.
    start_node_id : int | None
        Stored as metadata in the resulting ``ProjectCommands``.
    only_first : bool
        If *True*, include only the first node in the range.

    Returns
    -------
    ProjectCommands
        The assembled commands, or a ``str`` error message on failure.
    """
    if end_index is None:
        end_index = len(sorted_nodes)

    nodes_slice = sorted_nodes[start_index:end_index]
    if not nodes_slice:
        return "No commands to run."

    project_commands = ProjectCommands(
        start_node_id=start_node_id if start_node_id is not None else -1,
        end_node_id=nodes_slice[-1].id(),
        node_commands_list=[],
    )

    for node_obj in nodes_slice:
        node_cmd = NodeCommands(index=node_obj.id(), node_data=node_obj.nodeData(), cmd_list=[])

        bs = node_obj.buildSettings()
        build_root = bs.build_dir
        install_root = bs.install_dir
        build_type = bs.build_type
        toolchain_path = bs.toolchain_file
        prefix_path = bs.prefix_path
        generator = bs.generator
        c_compiler = bs.c_compiler
        cxx_compiler = bs.cxx_compiler

        project_name = node_obj.title()
        safe_project_name = _sanitize_name(project_name)
        project_dir = node_obj.projectPath()

        # Pre-configure script
        if stage in ("configure", "all") and node_obj.codeBeforeBuild().strip():
            node_cmd.cmd_list.append(CommandData(
                type="script",
                cmd=node_obj.codeBeforeBuild(),
                display_name=f"Pre-Configure Script {project_name}",
            ))

        if not project_dir or not os.path.isdir(project_dir):
            return f"{project_name} has invalid project path."

        cmake_lists_file = os.path.join(project_dir, "CMakeLists.txt")
        if not os.path.exists(cmake_lists_file):
            return f"CMakeLists.txt not found in {project_dir}."

        node_build_dir = os.path.join(
            build_root.format(build_type=build_type), safe_project_name,
        )
        node_install_dir = install_root.format(build_type=build_type)
        node_prefix_path = prefix_path.format(build_type=build_type) if prefix_path else ""
        os.makedirs(node_build_dir, exist_ok=True)

        # Configure command
        cmd_configure = [
            "cmake",
            "-S", project_dir,
            "-B", node_build_dir,
            f"-DCMAKE_BUILD_TYPE:STRING={build_type}",
            f"-DCMAKE_INSTALL_PREFIX={node_install_dir}",
        ]
        if generator:
            cmd_configure[1:1] = ["-G", generator]
        if c_compiler:
            cmd_configure.append(f"-DCMAKE_C_COMPILER:FILEPATH={c_compiler}")
        if cxx_compiler:
            cmd_configure.append(f"-DCMAKE_CXX_COMPILER:FILEPATH={cxx_compiler}")
        if toolchain_path:
            cmd_configure.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_path}")
        if node_prefix_path:
            cmd_configure.append(f"-DCMAKE_PREFIX_PATH={node_prefix_path}")
        # NOTE: {build_type} in build_dir / install_dir / prefix_path is
        #       resolved above via str.format(build_type=...).
        for opt in node_obj.cmakeOptions():
            cmd_configure.append(opt)

        if stage in ("configure", "all"):
            node_cmd.cmd_list.append(CommandData(
                type="cmd", cmd=cmd_configure, display_name=f"Configure {project_name}",
            ))

        # Build command
        cmd_build = [
            "cmake", "--build", node_build_dir,
            "--config", build_type,
            "--parallel", str(multiprocessing.cpu_count()),
        ]
        if stage in ("build", "all"):
            node_cmd.cmd_list.append(CommandData(
                type="cmd", cmd=cmd_build, display_name=f"Build {project_name}",
            ))

        # Install command
        cmd_install = ["cmake", "--install", node_build_dir, "--config", build_type]
        if stage in ("install", "all"):
            node_cmd.cmd_list.append(CommandData(
                type="cmd", cmd=cmd_install, display_name=f"Install {project_name}",
            ))

            if node_obj.codeAfterInstall().strip():
                node_cmd.cmd_list.append(CommandData(
                    type="script",
                    cmd=node_obj.codeAfterInstall(),
                    display_name=f"Post-Install Script {project_name}",
                ))

        project_commands.node_commands_list.append(node_cmd)
        if only_first:
            break

    if not project_commands.node_commands_list:
        return "No commands to run."

    return project_commands

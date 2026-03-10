"""
Command builder service.

Assembles :class:`ProjectCommands` by delegating per-node command generation
to the appropriate :class:`BuildStrategy`.  The public entry point
:func:`build_project_commands` iterates a topologically sorted node list,
resolves path templates, and collects the results.

Any object that exposes ``id()``, ``title()``, ``projectPath()``,
``buildSettings()``, ``cmakeOptions()``, ``codeBeforeBuild()``,
``codeAfterInstall()``, ``nodeData()``, ``buildSystem()``, and
``customCommands()`` is accepted (duck typing).
This allows both :class:`NodeItem` (GUI) and :class:`NodeProxy` (CLI) to
be used interchangeably.
"""

from __future__ import annotations

import os

from ..models.data_classes import (
    ProjectCommands, NodeCommands, CommandData, NodeData, BuildSettings,
    CustomCommands,
)
from .build_strategies import get_strategy
from .path_resolver import make_path_context, validate_template, resolve_path


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

    def buildSystem(self) -> str:
        return self._data.build_system

    def customCommands(self) -> CustomCommands | None:
        return self._data.custom_commands


def build_project_commands(
    sorted_nodes,
    *,
    stage: str = "build",
    start_index: int = 0,
    end_index: int | None = None,
    start_node_id: int | None = None,
    only_first: bool = False,
    build_type_override: str | None = None,
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
    build_type_override : str | None
        If set, overrides every node's ``build_type`` for path
        resolution and command generation.

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
        bs = node_obj.buildSettings()
        project_dir = node_obj.projectPath()
        ctx = make_path_context(node_obj, build_type_override)

        # Validate templates before resolving
        for attr, template in [
            ("build_dir", bs.build_dir),
            ("install_dir", bs.install_dir),
            ("prefix_path", bs.prefix_path),
        ]:
            unknown = validate_template(template, ctx)
            if unknown:
                return (
                    f"Node '{node_obj.title()}': unknown variable(s) "
                    f"in {attr}: {{{', '.join(unknown)}}}"
                )

        # Resolve path templates
        node_build_dir = resolve_path(bs.build_dir, ctx)
        node_install_dir = resolve_path(bs.install_dir, ctx)
        node_prefix_path = resolve_path(bs.prefix_path, ctx) if bs.prefix_path else ""
        build_type = ctx.as_dict()["build_type"]

        # Delegate to the appropriate strategy
        strategy = get_strategy(node_obj.buildSystem())

        err = strategy.validate(node_obj, project_dir)
        if err:
            return err

        cmd_list = strategy.generate_commands(
            node_obj, stage, node_build_dir, node_install_dir, node_prefix_path,
            build_type,
        )

        node_cmd = NodeCommands(
            index=node_obj.id(), node_data=node_obj.nodeData(), cmd_list=cmd_list,
        )
        project_commands.node_commands_list.append(node_cmd)

        if only_first:
            break

    if not project_commands.node_commands_list:
        return "No commands to run."

    return project_commands

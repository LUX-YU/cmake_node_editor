"""
Headless (no-Qt) builder — loads a project JSON and executes CMake commands
synchronously in the current process.

This module has **zero** PyQt dependency and can be used from a plain CLI.
"""

from __future__ import annotations

import os
import sys
import subprocess
import traceback
from collections import deque

from ..models.data_classes import (
    NodeData, BuildSettings, ProjectCommands,
    SubprocessLogData, SubprocessResponseData,
)
from ..scene.serialization import load_project
from .cmake_command_builder import NodeProxy, build_project_commands


# ---------------------------------------------------------------------------
# Lightweight topological sort on NodeData / edge dicts
# ---------------------------------------------------------------------------

def _topo_sort(
    node_datas: list[NodeData],
    edge_dicts: list[dict],
) -> list[NodeData] | None:
    """Kahn's algorithm over plain :class:`NodeData` + edge dicts.

    Returns *None* on cycle detection.
    """
    id_to_nd = {nd.node_id: nd for nd in node_datas}
    adjacency: dict[int, list[int]] = {nd.node_id: [] for nd in node_datas}
    in_degree: dict[int, int] = {nd.node_id: 0 for nd in node_datas}

    for ed in edge_dicts:
        src = ed["source_node_id"]
        dst = ed["target_node_id"]
        if src in adjacency and dst in adjacency:
            adjacency[src].append(dst)
            in_degree[dst] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    result: list[int] = []
    while queue:
        nid = queue.popleft()
        result.append(nid)
        for child in adjacency[nid]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(result) != len(node_datas):
        return None  # cycle

    return [id_to_nd[nid] for nid in result]


# ---------------------------------------------------------------------------
# Project info (for ``cmake-node-cli info``)
# ---------------------------------------------------------------------------

def project_info(filepath: str) -> str:
    """Return a human-readable summary of the project JSON."""
    global_cfg, node_datas, edge_dicts = load_project(filepath)

    lines: list[str] = []
    lines.append(f"Project file : {os.path.abspath(filepath)}")
    lines.append(f"Nodes        : {len(node_datas)}")
    lines.append(f"Edges        : {len(edge_dicts)}")
    lines.append("")

    # Topology
    sorted_nodes = _topo_sort(node_datas, edge_dicts)
    if sorted_nodes is None:
        lines.append("WARNING: Circular dependency detected — cannot determine build order.")
        lines.append("")
        sorted_nodes = node_datas  # fallback: just list them

    lines.append("Build order (topological):")
    lines.append("-" * 60)
    for i, nd in enumerate(sorted_nodes):
        bs = nd.build_settings
        lines.append(f"  {i+1}. [{nd.node_id}] {nd.title}")
        lines.append(f"       project_path  : {nd.project_path}")
        lines.append(f"       build_dir     : {bs.build_dir}")
        lines.append(f"       install_dir   : {bs.install_dir}")
        lines.append(f"       build_type    : {bs.build_type}")
        if bs.generator:
            lines.append(f"       generator     : {bs.generator}")
        if bs.toolchain_file:
            lines.append(f"       toolchain     : {bs.toolchain_file}")
        if bs.prefix_path:
            lines.append(f"       prefix_path   : {bs.prefix_path}")
        if bs.c_compiler:
            lines.append(f"       c_compiler    : {bs.c_compiler}")
        if bs.cxx_compiler:
            lines.append(f"       cxx_compiler  : {bs.cxx_compiler}")
        if nd.cmake_options:
            lines.append(f"       cmake_options : {nd.cmake_options}")
        if nd.code_before_build.strip():
            lines.append(f"       pre-script    : yes ({len(nd.code_before_build)} chars)")
        if nd.code_after_install.strip():
            lines.append(f"       post-script   : yes ({len(nd.code_after_install)} chars)")

    if edge_dicts:
        lines.append("")
        lines.append("Edges:")
        lines.append("-" * 60)
        id_to_title = {nd.node_id: nd.title for nd in node_datas}
        for ed in edge_dicts:
            src, dst = ed["source_node_id"], ed["target_node_id"]
            lines.append(
                f"  [{src}] {id_to_title.get(src, '?')}  -->  "
                f"[{dst}] {id_to_title.get(dst, '?')}"
            )

    lines.append("")
    lines.append("Available stages : configure, build, install, all")
    lines.append(f"Valid node IDs   : {', '.join(str(nd.node_id) for nd in sorted_nodes)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Synchronous command executor (no Qt, no multiprocessing)
# ---------------------------------------------------------------------------

class _SyncExecutor:
    """Execute commands in-process with real-time stdout streaming."""

    TIMEOUT = 3600

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, msg: str):
        if self.verbose:
            print(msg, flush=True)

    def execute(self, cmd_data) -> bool:
        if cmd_data.type == "script":
            return self._run_script(cmd_data)
        if cmd_data.type == "cmd":
            return self._run_cmd(cmd_data)
        self.log(f"[CLI] Unknown command type: {cmd_data.type}")
        return False

    def _run_script(self, cmd_data) -> bool:
        import tempfile
        self.log(f"[CLI] Running script: {cmd_data.display_name}")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(cmd_data.cmd)
            tmp_path = tmp.name
        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                check=False, timeout=self.TIMEOUT,
            )
            if proc.returncode != 0:
                self.log(f"[CLI] Script FAILED (rc={proc.returncode}): {cmd_data.display_name}")
                return False
            self.log(f"[CLI] Script OK: {cmd_data.display_name}")
            return True
        except subprocess.TimeoutExpired:
            self.log(f"[CLI] Script TIMEOUT: {cmd_data.display_name}")
            return False
        finally:
            os.unlink(tmp_path)

    def _run_cmd(self, cmd_data) -> bool:
        self.log(f"[CLI] Running: {' '.join(cmd_data.cmd)}")
        try:
            proc = subprocess.run(
                cmd_data.cmd, check=False, timeout=self.TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            self.log(f"[CLI] TIMEOUT: {cmd_data.display_name}")
            return False
        if proc.returncode != 0:
            self.log(f"[CLI] FAILED (rc={proc.returncode}): {cmd_data.display_name}")
            return False
        self.log(f"[CLI] OK: {cmd_data.display_name}")
        return True


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def headless_build(
    filepath: str,
    stage: str = "all",
    start_node_id: int | None = None,
    end_node_id: int | None = None,
    only_first: bool = False,
    verbose: bool = True,
    load_vcvars: bool = True,
) -> bool:
    """
    Load *filepath*, topo-sort, generate commands, execute synchronously.

    Returns *True* on success, *False* on failure.
    """
    from .worker import find_vcvarsall, load_vcvars_env

    # Optionally load VS developer environment on Windows
    if load_vcvars and os.name == "nt":
        vc = find_vcvarsall()
        if vc:
            try:
                load_vcvars_env(vc, arch="x64")
                if verbose:
                    print("[CLI] Loaded vcvarsall.bat environment.")
            except Exception as e:
                if verbose:
                    print(f"[CLI] Warning: failed to load vcvarsall.bat: {e}")

    # Load project
    _global_cfg, node_datas, edge_dicts = load_project(filepath)

    # Topo sort
    sorted_datas = _topo_sort(node_datas, edge_dicts)
    if sorted_datas is None:
        print("[CLI] ERROR: Circular dependency detected, cannot build.", file=sys.stderr)
        return False

    # Wrap as NodeProxy for build_project_commands
    sorted_proxies = [NodeProxy(nd) for nd in sorted_datas]

    # Determine start/end indices
    start_index = 0
    if start_node_id is not None:
        for idx, p in enumerate(sorted_proxies):
            if p.id() == start_node_id:
                start_index = idx
                break
        else:
            print(f"[CLI] ERROR: Start node ID {start_node_id} not found.", file=sys.stderr)
            return False

    end_index = len(sorted_proxies)
    if end_node_id is not None:
        for idx, p in enumerate(sorted_proxies):
            if p.id() == end_node_id:
                end_index = idx + 1
                break
        else:
            print(f"[CLI] ERROR: End node ID {end_node_id} not found.", file=sys.stderr)
            return False

    if end_index <= start_index:
        print("[CLI] ERROR: Invalid node range.", file=sys.stderr)
        return False

    # Build commands
    result = build_project_commands(
        sorted_proxies,
        stage=stage,
        start_index=start_index,
        end_index=end_index,
        start_node_id=start_node_id,
        only_first=only_first,
    )
    if isinstance(result, str):
        print(f"[CLI] ERROR: {result}", file=sys.stderr)
        return False

    project_commands: ProjectCommands = result

    # Execute synchronously
    executor = _SyncExecutor(verbose=verbose)
    total = len(project_commands.node_commands_list)
    if verbose:
        print(f"[CLI] Executing {total} node(s), stage={stage}")

    for i, node_cmds in enumerate(project_commands.node_commands_list):
        nd = node_cmds.node_data
        if verbose:
            print(f"\n{'='*60}")
            print(f"[CLI] [{i+1}/{total}] Node: {nd.title} (ID={nd.node_id})")
            print(f"{'='*60}")

        for cmd_data in node_cmds.cmd_list:
            ok = executor.execute(cmd_data)
            if not ok:
                print(f"\n[CLI] Build FAILED at node '{nd.title}'.", file=sys.stderr)
                return False

    if verbose:
        print(f"\n[CLI] All {total} node(s) completed successfully!")
    return True

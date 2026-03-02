"""
Data classes used throughout the CMake Node Editor.

All domain objects are plain ``@dataclass`` instances, which makes them easy
to serialize with ``dataclasses.asdict`` and transfer between processes via
``multiprocessing.Queue``.
"""

from dataclasses import dataclass, field


@dataclass
class BuildSettings:
    build_dir: str
    install_dir: str
    build_type: str
    prefix_path: str
    toolchain_file: str
    generator: str
    c_compiler: str = ""
    cxx_compiler: str = ""


@dataclass
class CustomCommands:
    """Three-stage user-defined scripts for non-CMake build systems."""
    configure_script: str = ""
    build_script: str = ""
    install_script: str = ""


@dataclass
class NodeData:
    node_id: int
    title: str
    pos_x: float
    pos_y: float
    cmake_options: list[str]
    project_path: str
    build_settings: BuildSettings
    code_before_build: str = ""
    code_after_install: str = ""
    build_system: str = "cmake"
    custom_commands: CustomCommands | None = None


@dataclass
class EdgeData:
    source_node_id: int
    target_node_id: int


@dataclass
class CommandData:
    type: str  # "cmd" or "script"
    cmd: str | list[str]
    display_name: str


@dataclass
class NodeCommands:
    index: int
    node_data: NodeData
    cmd_list: list[CommandData] = field(default_factory=list)


@dataclass
class ProjectCommands:
    start_node_id: int
    end_node_id: int = -1
    node_commands_list: list[NodeCommands] = field(default_factory=list)


@dataclass
class SubprocessResponseData:
    index: int
    result: bool


@dataclass
class SubprocessLogData:
    """Log message produced by the worker subprocess."""
    index: int
    log: str

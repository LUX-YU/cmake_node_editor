from dataclasses import dataclass, is_dataclass, asdict, field, fields
from PyQt6.QtWidgets import QGraphicsPathItem
import json


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

@dataclass
class EdgeData:
    source_node_id : int
    target_node_id : int


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
    index : int
    result : bool

# 用于传递子进程的输出
@dataclass
class SubprocessLogData:
    index : int
    log : str

def to_json(data, indent=4, ensure_ascii=False):
    if is_dataclass(data):
        return json.dumps(asdict(data), indent, ensure_ascii)
    else:
        return json.dumps(data, indent, ensure_ascii)
    
def from_json(json_str, data_class):
    data_dict = json.loads(json_str)
    def _construct(value, cls):
        if is_dataclass(cls) and isinstance(value, dict):
            kwargs = {}
            for f in fields(cls):
                if f.name in value:
                    kwargs[f.name] = _construct(value[f.name], f.type)
            return cls(**kwargs)
        origin = getattr(cls, "__origin__", None)
        if origin is list and isinstance(value, list):
            item_type = cls.__args__[0]
            return [_construct(v, item_type) for v in value]
        return value

    return _construct(data_dict, data_class)

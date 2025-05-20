import sys
import types

# Provide dummy PyQt6 modules if PyQt6 is not installed
if 'PyQt6' not in sys.modules:
    pyqt6 = types.ModuleType('PyQt6')
    qtwidgets = types.ModuleType('PyQt6.QtWidgets')
    class DummyPathItem: pass
    qtwidgets.QGraphicsPathItem = DummyPathItem
    pyqt6.QtWidgets = qtwidgets
    sys.modules['PyQt6'] = pyqt6
    sys.modules['PyQt6.QtWidgets'] = qtwidgets

from cmake_node_editor.datas import BuildSettings, NodeData, to_json, from_json


def test_nested_dataclass_from_json():
    settings = BuildSettings(
        build_dir="build",
        install_dir="install",
        build_type="Debug",
        prefix_path="/usr/local",
        toolchain_file="toolchain.cmake",
        generator="Ninja",
        c_compiler="gcc",
        cxx_compiler="g++",
    )
    node = NodeData(
        node_id=1,
        title="Test",
        pos_x=0.0,
        pos_y=0.0,
        cmake_options=["-DUSE_TEST=ON"],
        project_path="/tmp/project",
        build_settings=settings,
    )
    json_str = to_json(node)
    loaded = from_json(json_str, NodeData)
    assert isinstance(loaded.build_settings, BuildSettings)
    assert loaded == node

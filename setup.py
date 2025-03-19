# setup.py
import setuptools

setuptools.setup(
    name="cmake_node_editor",
    version="0.1.0",
    packages=["cmake_node_editor"],
    install_requires=["PyQt6"],  # 需要先安装PyQt6
    entry_points={
        "console_scripts": [
            "cmake-node-editor = cmake_node_editor.main:main",  
        ],
    },
)

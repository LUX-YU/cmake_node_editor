# setup.py
import setuptools

setuptools.setup(
    name="cmake_node_editor",
    version="0.1.0",
    packages=setuptools.find_packages(),
    install_requires=["PyQt6"],
    entry_points={
        "console_scripts": [
            "cmake-node-editor = cmake_node_editor.main:main",
            "cmake-node-cli = cmake_node_editor.cli:main",
        ],
    },
)

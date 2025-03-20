# CMake Conductor
## Overview

This project is a node editor built with **PyQt6** that integrates a multiprocessing build system for managing and building projects with **CMake**. The application allows you to create and manage nodes, each representing a build unit with a node name, multiple CMake options, a project folder (which must contain a `CMakeLists.txt`), and optional pre-build and post-install scripts. It uses topological sorting to determine the build order and ensure dependencies are built correctly, while asynchronously executing build commands in a subprocess and providing real-time log feedback.

## Features
- **Node Creation and Management**
  - Use a dialog to input the node name, multiple CMake options, and the project path.
  - Nodes can include pre-build and post-install scripts to customize the build process.

- **Graphical User Interface**
  - Intuitive UI built with PyQt6 that supports drag-and-drop, zooming, selection, and connection operations.
  - Dockable panels for build logs, node properties, global build settings, and topology order display.

- **Topological Sorting**
  - Nodes are sorted based on dependencies (output-to-input connections).
  - The system detects circular dependencies and notifies the user.

- **Multiprocessing Build Execution**
  - Utilizes Python's multiprocessing module to execute build commands and scripts in a subprocess.
  - Provides real-time logging and build status updates via inter-process communication.

- **Project Save and Load**
  - Save the global configuration, node data, and connection information to a JSON file.
  - Load previously saved projects to restore the state of the node editor.

## Requirements

- Python 3.x
- [PyQt6](https://pypi.org/project/PyQt6/)
- CMake (for executing build commands)

## How to Use

1. **Launch the Application**  
   Run `python -m cmake_node_editor.main`

# CMake Conductor

CMake Conductor is a user-friendly application designed to simplify the management and building of projects with CMake. It provides an intuitive, visual interface to organize your build steps, manage dependencies, and monitor the build process in real time.

## Interface
![screenshot](/assets/Screenshot.png)

## What It Does
- **Visual Build Organization**: Represent different parts of your project as individual build units (nodes) that can be arranged and connected.
- **Streamlined Workflow**: Easily set up and manage custom build steps without dealing with complex command line instructions.
- **Real-Time Monitoring**: View build progress and logs as your project is built, making it simple to spot and address issues.

The "Settings" option in the **File** menu lets you change the application style and adjust the background grid transparency.

## How to Use

### GUI Mode

1. **Launch the Application**  
   Open your terminal and run:
   ```bash
   python -m cmake_node_editor
   ```

2. **Create Nodes**: Right-click the canvas → "Create Node", or use **Edit → Add Node**. Select a project folder (must contain `CMakeLists.txt`), the node name is auto-filled from the folder name.

3. **Connect Nodes**: Drag from an output pin to an input pin to create dependency edges.

4. **Build**: Use the **Project** menu to run Configure / Build / Install on the entire graph or a selected range.

5. **Save / Load**: **File → Save** (`Ctrl+S`) persists the graph to a JSON file that can be reloaded later or used with the CLI.

### CLI Mode (Headless)

Build projects from the command line without launching the GUI. **No PyQt dependency required** for CLI usage.

#### Show Project Info

```bash
python -m cmake_node_editor.cli info project.json
```

Displays a full summary of the project: node list with all settings, topological build order, dependency edges, available stages, and valid node IDs.

Example output:
```
Project file : /path/to/project.json
Nodes        : 3
Edges        : 2

Build order (topological):
------------------------------------------------------------
  1. [1] libfoo
       project_path  : /repos/libfoo
       build_dir     : build
       install_dir   : install
       build_type    : Release
       generator     : Ninja
  2. [2] libbar
       ...
  3. [3] app_main
       ...

Edges:
------------------------------------------------------------
  [1] libfoo  -->  [3] app_main
  [2] libbar  -->  [3] app_main

Available stages : configure, build, install, all
Valid node IDs   : 1, 2, 3
```

#### Build

```bash
# Full generate (configure + build + install) for all nodes
python -m cmake_node_editor.cli build project.json

# Only configure stage
python -m cmake_node_editor.cli build project.json --stage configure

# Build from node 2 to node 5
python -m cmake_node_editor.cli build project.json --stage build --start 2 --end 5

# Install only the first node
python -m cmake_node_editor.cli build project.json --stage install --start 1 --only-first

# Quiet mode (errors only), skip VS environment loading
python -m cmake_node_editor.cli build project.json -q --no-vcvars
```

| Option | Description |
|---|---|
| `--stage`, `-s` | `configure` / `build` / `install` / `all` (default: `all`) |
| `--start NODE_ID` | Start from this node ID (inclusive) |
| `--end NODE_ID` | Stop after this node ID (inclusive) |
| `--only-first` | Execute only the first node in the range |
| `--no-vcvars` | Skip loading Visual Studio developer environment (Windows) |
| `-q`, `--quiet` | Suppress informational output; only print errors |

## Installation

```bash
pip install -e .
```

This registers two console commands:
- `cmake-node-editor` — launches the GUI
- `cmake-node-cli` — headless CLI builder

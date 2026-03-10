"""
Centralized constants and default values for CMake Node Editor.

All magic numbers, default paths, and configuration values that were
previously scattered across multiple files are collected here.
"""

# ---------------------------------------------------------------------------
# Node rendering
# ---------------------------------------------------------------------------
NODE_WIDTH = 190
NODE_HEIGHT = 82
PIN_SIZE = 12          # diameter of the circular connector
NODE_CORNER_RADIUS = 9
NODE_HEADER_HEIGHT = 28
NODE_GLOW_MARGIN = 12  # extra pixels around node bounding rect for glow

# ---------------------------------------------------------------------------
# Scene / Grid
# ---------------------------------------------------------------------------
GRID_SIZE = 20
DEFAULT_GRID_OPACITY = 0.5
NODE_AUTO_OFFSET_X = 30
NODE_AUTO_OFFSET_Y = 30
NODE_INITIAL_X = 100
NODE_INITIAL_Y = 100

# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------
ZOOM_SCALE_FACTOR = 1.15

# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
WINDOW_TITLE = "QNode Editor for cmake projects"

# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
SAVE_FORMAT_VERSION: int = 2

# ---------------------------------------------------------------------------
# CMake defaults
# ---------------------------------------------------------------------------
DEFAULT_BUILD_DIR = "build/{build_type}/{project_name}"
DEFAULT_INSTALL_DIR = "install/{build_type}"
DEFAULT_BUILD_TYPE = "Debug"

BUILD_TYPES = ["Debug", "Release", "RelWithDebInfo", "MinSizeRel"]

GENERATORS = [
    "Default (not specified)",
    "Visual Studio 17 2022",
    "Visual Studio 16 2019",
    "Ninja",
    "Unix Makefiles",
]

"""
CMake build strategy — extracted from the monolithic ``cmake_command_builder``.
"""

from __future__ import annotations

import multiprocessing
import os
from typing import TYPE_CHECKING, Any

from .base import BuildStrategy
from ...models.data_classes import CommandData

if TYPE_CHECKING:
    from ...views.graphics_items import NodeItem


class CMakeStrategy(BuildStrategy):
    """Generate configure / build / install commands for a CMake project."""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "cmake"

    @property
    def label(self) -> str:
        return "CMake"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_project_dir(self, project_dir: str) -> str | None:
        if not os.path.exists(os.path.join(project_dir, "CMakeLists.txt")):
            return "No CMakeLists.txt found in that folder."
        return None

    def validate(self, node: Any, project_dir: str) -> str | None:
        if not project_dir or not os.path.isdir(project_dir):
            return f"{node.title()} has invalid project path."
        cmake_lists = os.path.join(project_dir, "CMakeLists.txt")
        if not os.path.exists(cmake_lists):
            return f"CMakeLists.txt not found in {project_dir}."
        return None

    # ------------------------------------------------------------------
    # BuildSettings metadata
    # ------------------------------------------------------------------

    def relevant_build_setting_keys(self) -> list[str]:
        return [
            "build_dir", "install_dir",
            "prefix_path", "toolchain_file", "generator",
            "c_compiler", "cxx_compiler",
        ]

    # ------------------------------------------------------------------
    # Inheritance
    # ------------------------------------------------------------------

    def copyable_node_attrs(self) -> list[tuple[str, str]]:
        return [("cmake_options", "CMake Options")]

    def copy_node_data(
        self,
        target_node: "NodeItem",
        source_node: "NodeItem",
        selected_keys: set[str],
    ) -> None:
        if "cmake_options" in selected_keys:
            target_node.setCMakeOptions(list(source_node.cmakeOptions()))

    # ------------------------------------------------------------------
    # Properties form
    # ------------------------------------------------------------------

    def create_properties_form(self) -> Any:
        from ...dialogs.widgets.cmake_strategy_form import CMakeStrategyForm
        return CMakeStrategyForm()

    # ------------------------------------------------------------------
    # Command generation
    # ------------------------------------------------------------------

    def generate_commands(
        self,
        node,
        stage: str,
        build_dir: str,
        install_dir: str,
        prefix_path: str,
        build_type: str = "",
    ) -> list[CommandData]:
        commands: list[CommandData] = []
        project_name = node.title()
        project_dir = node.projectPath()
        bs = node.buildSettings()
        if not build_type:
            build_type = bs.build_type

        # Pre-configure script
        if stage in ("configure", "all") and node.codeBeforeBuild().strip():
            commands.append(CommandData(
                type="script",
                cmd=node.codeBeforeBuild(),
                display_name=f"Pre-Configure Script {project_name}",
            ))

        os.makedirs(build_dir, exist_ok=True)

        # Configure
        cmd_configure = [
            "cmake",
            "-S", project_dir,
            "-B", build_dir,
            f"-DCMAKE_BUILD_TYPE:STRING={build_type}",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        ]
        if bs.generator:
            cmd_configure[1:1] = ["-G", bs.generator]
        if bs.c_compiler:
            cmd_configure.append(f"-DCMAKE_C_COMPILER:FILEPATH={bs.c_compiler}")
        if bs.cxx_compiler:
            cmd_configure.append(f"-DCMAKE_CXX_COMPILER:FILEPATH={bs.cxx_compiler}")
        if bs.toolchain_file:
            cmd_configure.append(f"-DCMAKE_TOOLCHAIN_FILE={bs.toolchain_file}")
        if prefix_path:
            cmd_configure.append(f"-DCMAKE_PREFIX_PATH={prefix_path}")
        for opt in node.cmakeOptions():
            cmd_configure.append(opt)

        if stage in ("configure", "all"):
            commands.append(CommandData(
                type="cmd", cmd=cmd_configure,
                display_name=f"Configure {project_name}",
            ))

        # Build
        cmd_build = [
            "cmake", "--build", build_dir,
            "--config", build_type,
            "--parallel", str(multiprocessing.cpu_count()),
        ]
        if stage in ("build", "all"):
            commands.append(CommandData(
                type="cmd", cmd=cmd_build,
                display_name=f"Build {project_name}",
            ))

        # Install
        cmd_install = ["cmake", "--install", build_dir, "--config", build_type]
        if stage in ("install", "all"):
            commands.append(CommandData(
                type="cmd", cmd=cmd_install,
                display_name=f"Install {project_name}",
            ))
            if node.codeAfterInstall().strip():
                commands.append(CommandData(
                    type="script",
                    cmd=node.codeAfterInstall(),
                    display_name=f"Post-Install Script {project_name}",
                ))

        return commands

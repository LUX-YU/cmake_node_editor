"""
CMake build strategy — extracted from the monolithic ``cmake_command_builder``.
"""

from __future__ import annotations

import multiprocessing
import os

from .base import BuildStrategy
from ...models.data_classes import CommandData


class CMakeStrategy(BuildStrategy):
    """Generate configure / build / install commands for a CMake project."""

    def validate(self, node, project_dir: str) -> str | None:
        if not project_dir or not os.path.isdir(project_dir):
            return f"{node.title()} has invalid project path."
        cmake_lists = os.path.join(project_dir, "CMakeLists.txt")
        if not os.path.exists(cmake_lists):
            return f"CMakeLists.txt not found in {project_dir}."
        return None

    def generate_commands(
        self,
        node,
        stage: str,
        build_dir: str,
        install_dir: str,
        prefix_path: str,
    ) -> list[CommandData]:
        commands: list[CommandData] = []
        project_name = node.title()
        project_dir = node.projectPath()
        bs = node.buildSettings()
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

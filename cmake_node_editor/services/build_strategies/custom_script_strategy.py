"""
Custom-script build strategy — fully user-defined shell commands.

Supports non-CMake build systems (Boost b2, Autotools, hand-written scripts, etc.)
by letting users write shell commands for each stage.
"""

from __future__ import annotations

import os

from .base import BuildStrategy
from ...models.data_classes import CommandData


class CustomScriptStrategy(BuildStrategy):
    """Generate commands from user-provided shell scripts."""

    def validate(self, node, project_dir: str) -> str | None:
        if not project_dir or not os.path.isdir(project_dir):
            return f"{node.title()} has invalid project path."
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
        cc = node.customCommands()
        if cc is None:
            return commands

        os.makedirs(build_dir, exist_ok=True)

        # Pre-configure script (Python, shared with CMake)
        if stage in ("configure", "all") and node.codeBeforeBuild().strip():
            commands.append(CommandData(
                type="script",
                cmd=node.codeBeforeBuild(),
                display_name=f"Pre-Configure Script {project_name}",
            ))

        # Configure
        if stage in ("configure", "all") and cc.configure_script.strip():
            commands.append(CommandData(
                type="shell",
                cmd=cc.configure_script,
                display_name=f"Configure {project_name}",
            ))

        # Build
        if stage in ("build", "all") and cc.build_script.strip():
            commands.append(CommandData(
                type="shell",
                cmd=cc.build_script,
                display_name=f"Build {project_name}",
            ))

        # Install
        if stage in ("install", "all") and cc.install_script.strip():
            commands.append(CommandData(
                type="shell",
                cmd=cc.install_script,
                display_name=f"Install {project_name}",
            ))
            if node.codeAfterInstall().strip():
                commands.append(CommandData(
                    type="script",
                    cmd=node.codeAfterInstall(),
                    display_name=f"Post-Install Script {project_name}",
                ))

        return commands

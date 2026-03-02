"""
Custom-script build strategy — fully user-defined shell commands.

Supports non-CMake build systems (Boost b2, Autotools, hand-written scripts, etc.)
by letting users write shell commands for each stage.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .base import BuildStrategy
from ...models.data_classes import CommandData, CustomCommands

if TYPE_CHECKING:
    from ...views.graphics_items import NodeItem


class CustomScriptStrategy(BuildStrategy):
    """Generate commands from user-provided shell scripts."""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "custom_script"

    @property
    def label(self) -> str:
        return "Custom Script"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, node: Any, project_dir: str) -> str | None:
        if not project_dir or not os.path.isdir(project_dir):
            return f"{node.title()} has invalid project path."
        return None

    # validate_project_dir: inherits default (any dir is fine)

    # ------------------------------------------------------------------
    # BuildSettings metadata — only generic fields
    # ------------------------------------------------------------------

    # relevant_build_setting_keys: inherits default ["build_dir", "install_dir", "build_type"]

    # ------------------------------------------------------------------
    # Inheritance
    # ------------------------------------------------------------------

    def copyable_node_attrs(self) -> list[tuple[str, str]]:
        return [("custom_commands", "Custom Commands (configure / build / install)")]

    def copy_node_data(
        self,
        target_node: "NodeItem",
        source_node: "NodeItem",
        selected_keys: set[str],
    ) -> None:
        if "custom_commands" in selected_keys:
            src_cc = source_node.customCommands()
            if src_cc:
                target_node.setCustomCommands(CustomCommands(
                    configure_script=src_cc.configure_script,
                    build_script=src_cc.build_script,
                    install_script=src_cc.install_script,
                ))

    # ------------------------------------------------------------------
    # Properties form
    # ------------------------------------------------------------------

    def create_properties_form(self) -> Any:
        from ...dialogs.widgets.custom_script_strategy_form import CustomScriptStrategyForm
        return CustomScriptStrategyForm()

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

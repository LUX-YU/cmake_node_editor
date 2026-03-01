"""
Auto-detect external code editors / IDEs installed on the system.

Returns a list of ``(display_name, executable_path)`` tuples that can be
used to open a project folder.
"""

from __future__ import annotations

import glob
import os
import platform
import shutil


def detect_editors() -> list[tuple[str, str]]:
    """Return ``[(display_name, exe_path), ...]`` for every detected editor.

    The list is deterministic and ordered by preference.
    """
    editors: list[tuple[str, str]] = []
    is_win = platform.system() == "Windows"

    # --- VS Code ---
    _try_which(editors, "code", "VS Code")
    _try_which(editors, "code-insiders", "VS Code Insiders")

    # --- Visual Studio (Windows only) ---
    if is_win:
        _detect_visual_studio(editors)

    # --- CLion ---
    _try_which(editors, "clion", "CLion")
    if is_win:
        _detect_clion_win(editors)

    # --- Sublime Text ---
    _try_which(editors, "subl", "Sublime Text")
    if is_win:
        _try_which(editors, "sublime_text", "Sublime Text")

    # --- Cursor ---
    _try_which(editors, "cursor", "Cursor")

    # --- Neovim / Vim (terminal) ---
    _try_which(editors, "nvim", "Neovim")

    # Deduplicate by resolved path (keep first occurrence)
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, exe in editors:
        real = os.path.realpath(exe)
        if real not in seen:
            seen.add(real)
            unique.append((name, exe))
    return unique


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _try_which(out: list[tuple[str, str]], cmd: str, label: str) -> None:
    exe = shutil.which(cmd)
    if exe:
        out.append((label, exe))


def _detect_visual_studio(out: list[tuple[str, str]]) -> None:
    """Scan common install locations for ``devenv.exe``."""
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pattern = os.path.join(pf, "Microsoft Visual Studio", "*", "*",
                           "Common7", "IDE", "devenv.exe")
    for path in sorted(glob.glob(pattern), reverse=True):
        # Extract version / edition from path components
        parts = path.replace("\\", "/").split("/")
        try:
            idx = parts.index("Microsoft Visual Studio")
            year = parts[idx + 1]
            edition = parts[idx + 2]
            label = f"Visual Studio {year} ({edition})"
        except (ValueError, IndexError):
            label = "Visual Studio"
        out.append((label, path))


def _detect_clion_win(out: list[tuple[str, str]]) -> None:
    """Scan JetBrains install paths for CLion on Windows."""
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pattern = os.path.join(pf, "JetBrains", "CLion*", "bin", "clion64.exe")
    for path in sorted(glob.glob(pattern), reverse=True):
        out.append(("CLion", path))

"""
Worker subprocess logic — executes cmake commands and scripts.

Moved from the top-level ``worker.py`` into ``services/`` with dead code
removed (``do_execute_command`` was unused).
"""

from __future__ import annotations

import sys
import os
import subprocess
import traceback
from multiprocessing import Queue

from ..models.data_classes import (
    ProjectCommands, NodeCommands, CommandData,
    SubprocessLogData, SubprocessResponseData,
)


class CommandExecutor:
    """Strategy class to execute different types of :class:`CommandData`."""

    SUBPROCESS_TIMEOUT = 3600  # 1 hour default timeout

    def __init__(self, result_queue: Queue):
        self.result_queue = result_queue

    def execute(self, cmd_data: CommandData) -> bool:
        try:
            if cmd_data.type == "script":
                return self._run_script(cmd_data)

            if cmd_data.type == "cmd":
                return self._run_cmd(cmd_data)

            self.result_queue.put(SubprocessLogData(
                index=-1, log=f"[Worker] Unknown command type: {cmd_data.type}"))
            return False

        except Exception as e:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            self.result_queue.put(SubprocessLogData(
                index=-1,
                log=f"[Worker] Exception while executing command: "
                    f"{cmd_data.display_name}\n{e}\n{tb}"))
            return False

    def _run_script(self, cmd_data: CommandData) -> bool:
        """Execute a Python script in an isolated subprocess."""
        self.result_queue.put(SubprocessLogData(
            index=-1, log=f"[Worker] Executing script: {cmd_data.display_name}"))

        # Write script to a temporary file and run in a subprocess for isolation
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(cmd_data.cmd)
            tmp_path = tmp.name

        try:
            run_res = subprocess.run(
                [sys.executable, tmp_path],
                check=False, capture_output=True, text=True,
                timeout=self.SUBPROCESS_TIMEOUT,
            )
            if run_res.stdout:
                self.result_queue.put(SubprocessLogData(index=-1, log=run_res.stdout))
            if run_res.stderr:
                self.result_queue.put(SubprocessLogData(index=-1, log=run_res.stderr))
            if run_res.returncode == 0:
                self.result_queue.put(SubprocessLogData(
                    index=-1, log=f"[Worker] Script executed successfully: {cmd_data.display_name}"))
                return True
            self.result_queue.put(SubprocessLogData(
                index=-1,
                log=f"[Worker] Script failed: {cmd_data.display_name}, "
                    f"returncode={run_res.returncode}"))
            return False
        except subprocess.TimeoutExpired:
            self.result_queue.put(SubprocessLogData(
                index=-1,
                log=f"[Worker] Script timed out ({self.SUBPROCESS_TIMEOUT}s): {cmd_data.display_name}"))
            return False
        finally:
            os.unlink(tmp_path)

    def _run_cmd(self, cmd_data: CommandData) -> bool:
        """Execute a system command with timeout protection."""
        self.result_queue.put(SubprocessLogData(
            index=-1,
            log=f"[Worker] Executing command: {cmd_data.display_name}\n{cmd_data.cmd}"))
        try:
            run_res = subprocess.run(
                cmd_data.cmd, check=False, capture_output=True, text=True,
                timeout=self.SUBPROCESS_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            self.result_queue.put(SubprocessLogData(
                index=-1,
                log=f"[Worker] Command timed out ({self.SUBPROCESS_TIMEOUT}s): {cmd_data.display_name}"))
            return False
        if run_res.stdout:
            self.result_queue.put(SubprocessLogData(index=-1, log=run_res.stdout))
        if run_res.stderr:
            self.result_queue.put(SubprocessLogData(index=-1, log=run_res.stderr))
        if run_res.returncode == 0:
            self.result_queue.put(SubprocessLogData(
                index=-1, log=f"[Worker] Command succeeded: {cmd_data.display_name}"))
            return True
        self.result_queue.put(SubprocessLogData(
            index=-1,
            log=f"[Worker] Command failed: {cmd_data.display_name}, "
                f"returncode={run_res.returncode}"))
        return False


# ---------------------------------------------------------------------------
# Visual Studio environment helpers (Windows only)
# ---------------------------------------------------------------------------

def find_vcvarsall() -> str | None:
    """Locate ``vcvarsall.bat`` via ``vswhere.exe``."""
    vswhere_path = r"C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
    if not os.path.exists(vswhere_path):
        return None

    result = subprocess.run(
        [vswhere_path, "-latest", "-products", "*",
         "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
         "-property", "installationPath"],
        capture_output=True, text=True,
    )
    installation_path = result.stdout.strip()
    if not installation_path:
        return None

    vcvarsall_path = os.path.join(installation_path, "VC", "Auxiliary", "Build", "vcvarsall.bat")
    return vcvarsall_path if os.path.exists(vcvarsall_path) else None


def load_vcvars_env(vcvarsall_path: str, arch: str = "x64"):
    """Run ``vcvarsall.bat`` and import its environment variables."""
    command = f'cmd /c "call \"{vcvarsall_path}\" {arch} && set"'
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, text=True)
    output, _ = proc.communicate()
    if output:
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value


# ---------------------------------------------------------------------------
# Worker main loop
# ---------------------------------------------------------------------------

def worker_main(task_queue: Queue, result_queue: Queue):
    """
    Entry point for the worker process.

    Reads :class:`ProjectCommands` from *task_queue*, executes them,
    and reports progress/results via *result_queue*.
    """
    # On Windows, load the Visual Studio developer environment.
    if os.name == "nt":
        vcvarsall_bat = find_vcvarsall()
        if vcvarsall_bat:
            try:
                load_vcvars_env(vcvarsall_bat, arch="x64")
                result_queue.put(SubprocessLogData(index=-1, log="[Worker] Loaded vcvarsall.bat environment."))
            except Exception as e:
                result_queue.put(SubprocessLogData(index=-1, log=f"[Worker] Failed to load vcvarsall.bat: {e}"))
        else:
            result_queue.put(SubprocessLogData(index=-1, log="[Worker] vswhere not found, skipping vcvarsall."))

    result_queue.put(SubprocessLogData(index=-1, log="[Worker] Worker process started."))

    executor = CommandExecutor(result_queue)

    while True:
        task = task_queue.get()
        if task is None or task == "QUIT":
            result_queue.put(SubprocessLogData(index=-1, log="[Worker] Received quit command, exiting..."))
            break

        if isinstance(task, ProjectCommands):
            result_queue.put(SubprocessLogData(index=-1, log="[Worker] Start executing ProjectCommands..."))
            build_failed = False
            try:
                for idx, node_cmds in enumerate(task.node_commands_list):
                    node_failed = False
                    for cmdData in node_cmds.cmd_list:
                        ok = executor.execute(cmdData)
                        if not ok:
                            result_queue.put(SubprocessResponseData(index=idx, result=False))
                            node_failed = True
                            build_failed = True
                            break
                    if not node_failed:
                        result_queue.put(SubprocessResponseData(index=idx, result=True))
                    if build_failed:
                        break

                if build_failed:
                    result_queue.put(SubprocessResponseData(index=-1, result=False))
                else:
                    result_queue.put(SubprocessLogData(index=-1, log="[Worker] All commands succeeded!"))
                    result_queue.put(SubprocessResponseData(index=-1, result=True))

            except Exception as e:
                traceback_str = "".join(traceback.format_exception(*sys.exc_info()))
                result_queue.put(SubprocessLogData(
                    index=-1, log=f"[Worker] Exception occurred: {e}\n{traceback_str}"))
                result_queue.put(SubprocessResponseData(index=-1, result=False))
        else:
            result_queue.put(SubprocessLogData(
                index=-1, log="[Worker] Received unknown task object, ignoring..."))

    result_queue.put(SubprocessLogData(index=-1, log="[Worker] Worker process finished."))

"""
worker.py

This module implements the logic for executing build commands in a worker subprocess.
It includes the following key functionalities:

  1. Automatically detect if the environment is Windows and, if so, load the Visual Studio
     developer environment by executing vcvarsall.bat.
  2. Automatically locate the Visual Studio installation path using vswhere and construct
     the full path to vcvarsall.bat (applicable for VS2017 and later).
  3. Retrieve ProjectCommands from the task queue and execute each NodeCommands and its
     associated CommandData sequentially.
  4. Send log messages (SubprocessLogData) and final execution statuses (SubprocessResponseData)
     back to the main process via the result queue.

Note: This module depends on data structures defined in the .datas module, including:
      ProjectCommands, NodeCommands, CommandData, SubprocessLogData, and SubprocessResponseData.
"""

import sys
import os
import subprocess
import traceback
from multiprocessing import Queue

from .datas import (
    ProjectCommands, NodeCommands, CommandData,
    SubprocessLogData, SubprocessResponseData
)

def find_vcvarsall():
    """
    Automatically locate the latest Visual Studio installation using vswhere
    and return the full path to vcvarsall.bat.

    For Visual Studio 2017 and later:
      - vswhere.exe is typically located at:
          "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
      - vcvarsall.bat is usually found at:
          <installationPath>/VC/Auxiliary/Build/vcvarsall.bat

    Raises:
      FileNotFoundError: If vswhere.exe or vcvarsall.bat cannot be found.
      RuntimeError: If vswhere fails to return a valid installation path.

    Returns:
      str: The full path to vcvarsall.bat.
    """
    vswhere_path = r"C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
    if not os.path.exists(vswhere_path):
        return None
    
    # Run vswhere to get the latest Visual Studio installation path that includes the VC tools.
    result = subprocess.run([
        vswhere_path,
        "-latest",
        "-products", "*",
        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property", "installationPath"
    ], capture_output=True, text=True)
    
    installation_path = result.stdout.strip()
    if not installation_path:
        return None
    
    # Construct the full path to vcvarsall.bat.
    vcvarsall_path = os.path.join(installation_path, "VC", "Auxiliary", "Build", "vcvarsall.bat")
    if not os.path.exists(vcvarsall_path):
        return None
    
    return vcvarsall_path

def load_vcvars_env(vcvarsall_path: str, arch: str = "x64"):
    """
    Calls vcvarsall.bat and loads its configured environment variables into os.environ.

    Implementation Details:
      - Uses cmd.exe to execute: call "<vcvarsall.bat>" <arch> && set
      - The 'set' command outputs all environment variables.
      - Parses each output line to update os.environ so that subsequent subprocess
        calls inherit the correct developer environment.

    Args:
      vcvarsall_path (str): The full path to vcvarsall.bat.
      arch (str): The target architecture (e.g., "x64", "x86"). Defaults to "x64".
    """
    command = f'cmd /c "call \"{vcvarsall_path}\" {arch} && set"'
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, text=True)
    output, _ = proc.communicate()
    if output:
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

def worker_main(task_queue: Queue, result_queue: Queue):
    """
    Main function for the worker process to execute build commands.

    Workflow:
      1. If running on Windows (os.name == "nt"), automatically locate and load the Visual Studio
         developer environment using vcvarsall.bat. This ensures tools like cl.exe and rc.exe are available.
      2. Continuously read tasks from the task_queue:
         - If the task is an instance of ProjectCommands, iterate through its NodeCommands and execute each CommandData.
         - Log each command's execution output to the result_queue.
         - If any command fails, send a failure status immediately.
         - If "QUIT" or None is received, exit the loop.
      3. Send a final log message indicating the worker process has finished.

    Args:
      task_queue (Queue): Queue from which tasks (ProjectCommands or quit commands) are received.
      result_queue (Queue): Queue for sending log messages (SubprocessLogData) and final statuses (SubprocessResponseData).
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

    while True:
        task = task_queue.get()
        if task is None or task == "QUIT":
            result_queue.put(SubprocessLogData(index=-1, log="[Worker] Received quit command, exiting..."))
            break

        if isinstance(task, ProjectCommands):
            result_queue.put(SubprocessLogData(index=-1, log="[Worker] Start executing ProjectCommands..."))
            build_failed = False
            try:
                # Iterate over each NodeCommands in the project.
                for idx, node_cmds in enumerate(task.node_commands_list):
                    node_failed = False
                    for cmdData in node_cmds.cmd_list:
                        ok = do_execute_command(cmdData, result_queue)
                        if not ok:
                            result_queue.put(SubprocessResponseData(index=idx, result=False))
                            node_failed = True
                            build_failed = True
                            break
                    if not node_failed:
                        result_queue.put(SubprocessResponseData(index=idx, result=True))
                    if build_failed:
                        break

                if not build_failed:
                    result_queue.put(SubprocessLogData(index=-1, log="[Worker] All commands succeeded!"))
                    result_queue.put(SubprocessResponseData(index=-1, result=True))

            except Exception as e:
                # Capture and log any exceptions along with their traceback.
                traceback_str = "".join(traceback.format_exception(*sys.exc_info()))
                result_queue.put(SubprocessLogData(index=-1, 
                    log=f"[Worker] Exception occurred: {e}\n{traceback_str}"))
                result_queue.put(SubprocessResponseData(index=-1, result=False))

        else:
            # Log and ignore unknown task types.
            result_queue.put(SubprocessLogData(index=-1, 
                log="[Worker] Received unknown task object, ignoring..."))

    result_queue.put(SubprocessLogData(index=-1, log="[Worker] Worker process finished."))

def do_execute_command(cmdData: CommandData, result_queue: Queue) -> bool:
    """
    Executes a single command or script and sends execution logs to the result_queue.

    Supports two types of commands:
      - "script": Executes a Python script via exec().
      - "cmd": Executes an external command using subprocess.run().

    Args:
      cmdData (CommandData): Object containing the command type, the command content, and a display name.
      result_queue (Queue): Queue for sending execution logs and error information.

    Returns:
      bool: True if the command executed successfully; False otherwise.
    """
    try:
        if cmdData.type == "script":
            result_queue.put(SubprocessLogData(index=-1,
                log=f"[Worker] Executing script: {cmdData.display_name}"))
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(cmdData.cmd, {}, {})
            out = buf.getvalue()
            if out:
                result_queue.put(SubprocessLogData(index=-1, log=out))
            result_queue.put(SubprocessLogData(index=-1,
                log=f"[Worker] Script executed successfully: {cmdData.display_name}"))
            return True

        elif cmdData.type == "cmd":
            result_queue.put(SubprocessLogData(index=-1, 
                log=f"[Worker] Executing command: {cmdData.display_name}\n{cmdData.cmd}"))
            
            # Execute the external command and capture its standard output and error.
            run_res = subprocess.run(cmdData.cmd, check=False, capture_output=True, text=True)
            if run_res.stdout:
                result_queue.put(SubprocessLogData(index=-1, log=run_res.stdout))
            if run_res.stderr:
                result_queue.put(SubprocessLogData(index=-1, log=run_res.stderr))
            
            if run_res.returncode == 0:
                result_queue.put(SubprocessLogData(index=-1, 
                    log=f"[Worker] Command succeeded: {cmdData.display_name}"))
                return True
            else:
                result_queue.put(SubprocessLogData(index=-1, 
                    log=f"[Worker] Command failed: {cmdData.display_name}, returncode={run_res.returncode}"))
                return False

        else:
            # Log an error for any unknown command type.
            result_queue.put(SubprocessLogData(index=-1, 
                log=f"[Worker] Unknown command type: {cmdData.type}"))
            return False

    except Exception as e:
        # Catch any exception during command execution, log detailed error info and traceback.
        tb = "".join(traceback.format_exception(*sys.exc_info()))
        result_queue.put(SubprocessLogData(index=-1, 
            log=f"[Worker] Exception while executing command: {cmdData.display_name}\n{e}\n{tb}"))
        return False

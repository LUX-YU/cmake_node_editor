import sys
import os
import subprocess
import traceback
from multiprocessing import Queue

from .datas import (
    ProjectCommands, NodeCommands, CommandData,
    SubprocessLogData, SubprocessResponseData
)

def worker_main(task_queue: Queue, result_queue: Queue):
    """
    The main function running in the worker process:
      - Waits for ProjectCommands (or 'QUIT') from the task_queue.
      - Iterates over each NodeCommands and CommandData, executing them.
      - Sends SubprocessLogData for logs, and SubprocessResponseData for success/fail to the result_queue.
    """
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
                # Process node commands in order
                for node_cmds in task.node_commands_list:
                    for cmdData in node_cmds.cmd_list:
                        # Execute a script or command
                        ok = do_execute_command(cmdData, result_queue)
                        if not ok:
                            # Build failure => inform main process with a final SubprocessResponseData
                            result_queue.put(SubprocessResponseData(index=-1, result=False))
                            build_failed = True
                            break
                    if build_failed:
                        break

                if not build_failed:
                    # All succeeded
                    result_queue.put(SubprocessLogData(index=-1, log="[Worker] All commands succeeded!"))
                    # Send a final response that everything is OK
                    result_queue.put(SubprocessResponseData(index=-1, result=True))

            except Exception as e:
                # If there's an exception, treat it as a failure
                traceback_str = "".join(traceback.format_exception(*sys.exc_info()))
                result_queue.put(SubprocessLogData(index=-1, 
                    log=f"[Worker] Exception occurred: {e}\n{traceback_str}"))
                result_queue.put(SubprocessResponseData(index=-1, result=False))

        else:
            # Unknown task object
            result_queue.put(SubprocessLogData(index=-1, 
                log="[Worker] Received unknown task object, ignoring..."))

    result_queue.put(SubprocessLogData(index=-1, log="[Worker] Worker process finished."))


def do_execute_command(cmdData: CommandData, result_queue: Queue) -> bool:
    """
    Execute a single command or script. Returns True on success, False on failure.
    Logs are sent to 'result_queue' as SubprocessLogData.
    """
    try:
        if cmdData.type == "script":
            result_queue.put(SubprocessLogData(index=-1, 
                log=f"[Worker] Executing script: {cmdData.display_name}"))
            # Evaluate the Python script
            exec(cmdData.cmd, {}, {})
            result_queue.put(SubprocessLogData(index=-1, 
                log=f"[Worker] Script executed successfully: {cmdData.display_name}"))
            return True

        elif cmdData.type == "cmd":
            # This is an external command (CMake, etc.)
            result_queue.put(SubprocessLogData(index=-1, 
                log=f"[Worker] Executing command: {cmdData.display_name}\n{cmdData.cmd}"))

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
            # Unknown command type
            result_queue.put(SubprocessLogData(index=-1, 
                log=f"[Worker] Unknown command type: {cmdData.type}"))
            return False

    except Exception as e:
        tb = "".join(traceback.format_exception(*sys.exc_info()))
        result_queue.put(SubprocessLogData(index=-1, 
            log=f"[Worker] Exception while executing command: {cmdData.display_name}\n{e}\n{tb}"))
        return False

"""
Worker process manager.

Handles spawning / stopping the background worker process and the
:class:`ResultListenerThread` that polls the result queue.
"""

from __future__ import annotations

import multiprocessing
from multiprocessing import Queue

from PyQt6.QtCore import QThread, pyqtSignal

from ..models.data_classes import SubprocessLogData, SubprocessResponseData, ProjectCommands
from ..services.worker import worker_main


class ResultListenerThread(QThread):
    """
    Background thread that reads from *result_queue* and re-emits data
    as Qt signals so the GUI thread can safely update widgets.
    """

    newLog = pyqtSignal(SubprocessLogData)
    newResponse = pyqtSignal(SubprocessResponseData)

    def __init__(self, result_queue: Queue, parent=None):
        super().__init__(parent)
        self.result_queue = result_queue
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self.result_queue.get(timeout=1.0)
            except Exception:
                continue

            if isinstance(data, SubprocessLogData):
                self.newLog.emit(data)
            elif isinstance(data, SubprocessResponseData):
                self.newResponse.emit(data)

    def stop(self):
        self._running = False


class WorkerManager:
    """
    Manages the lifecycle of the worker subprocess.

    Usage::

        wm = WorkerManager()
        wm.start()
        thread = wm.create_listener(log_cb, response_cb)
        wm.send(project_commands)
        ...
        wm.stop()
    """

    def __init__(self):
        self.task_queue: Queue | None = None
        self.result_queue: Queue | None = None
        self.worker_proc: multiprocessing.Process | None = None
        self.result_thread: ResultListenerThread | None = None

    # ------------------------------------------------------------------
    def start(self):
        """Create queues and spawn the worker process."""
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.worker_proc = multiprocessing.Process(
            target=worker_main,
            args=(self.task_queue, self.result_queue),
        )
        self.worker_proc.start()

    def create_listener(self, log_callback, response_callback) -> ResultListenerThread:
        """Start a :class:`ResultListenerThread` wired to the given callbacks."""
        self.result_thread = ResultListenerThread(self.result_queue)
        self.result_thread.newLog.connect(log_callback)
        self.result_thread.newResponse.connect(response_callback)
        self.result_thread.start()
        return self.result_thread

    def send(self, project_commands: ProjectCommands):
        """Put *project_commands* onto the task queue for the worker."""
        if self.task_queue is not None:
            self.task_queue.put(project_commands)

    def stop(self):
        """Gracefully stop the listener thread and worker process."""
        if self.result_thread:
            self.result_thread.stop()
            self.result_thread.wait(2000)
            self.result_thread = None

        if self.worker_proc and self.worker_proc.is_alive():
            if self.task_queue:
                self.task_queue.put("QUIT")
            self.worker_proc.join(timeout=2.0)
            if self.worker_proc.is_alive():
                self.worker_proc.terminate()

        self.worker_proc = None

    @property
    def is_running(self) -> bool:
        return self.worker_proc is not None and self.worker_proc.is_alive()

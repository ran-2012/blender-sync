"""Background task runner using threading.

Safe for Blender: the worker thread MUST NOT touch bpy.
All bpy-dependent data must be collected on the main thread first.
"""

import threading
import traceback


class BackgroundTask:
    """Run a function in a daemon thread and capture its result.

    Usage::

        task = BackgroundTask(some_func, arg1, arg2)
        task.start()
        # ... later, from a timer callback ...
        if task.is_done:
            result = task.result()  # raises if the function raised
    """

    def __init__(self, fn, *args, **kwargs):
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._result = None
        self._error = None
        self._done = False
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            self._result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:
            self._error = exc
            self._traceback = traceback.format_exc()
        self._done = True

    @property
    def is_done(self) -> bool:
        return self._done

    def result(self):
        """Return the function's return value or raise if it failed."""
        if self._error is not None:
            raise self._error
        return self._result

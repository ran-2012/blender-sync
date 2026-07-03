"""Debug logging for Blender Sync.

Writes to blender-sync-state/runtime/sync.log when enabled.
"""

import os
from datetime import datetime, timezone

_enabled = False
_log_path = None


def init(data_dir: str):
    """Set up the log path. Call once during SyncService init."""
    global _log_path
    runtime = os.path.join(data_dir, "runtime")
    os.makedirs(runtime, exist_ok=True)
    _log_path = os.path.join(runtime, "sync.log")


def enable():
    global _enabled
    _enabled = True


def disable():
    global _enabled
    _enabled = False


def is_enabled() -> bool:
    return _enabled


def info(msg: str):
    _write("INFO", msg)


def warn(msg: str):
    _write("WARN", msg)


def header(title: str):
    _write("====", f"  {title}  ".center(60, "="))


def _write(level: str, msg: str):
    if not _enabled or not _log_path:
        return
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] [{level}] {msg}\n"
    try:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass

"""Status store for persisting sync state."""

import json
import os
import tempfile
from datetime import datetime, timezone


def get_status_path(data_dir: str) -> str:
    """Get path to status.json."""
    runtime_dir = os.path.join(data_dir, "runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    return os.path.join(runtime_dir, "status.json")


def read_status(data_dir: str) -> dict:
    """Read current sync status. Returns default if not found."""
    path = get_status_path(data_dir)
    if not os.path.exists(path):
        return _default_status()

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_status()


def write_status(data_dir: str, status: dict) -> None:
    """Atomically write sync status."""
    path = get_status_path(data_dir)
    status["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Atomic write: write to temp then rename
    dir_name = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=dir_name,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        json.dump(status, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name

    os.replace(tmp_path, path)


def _default_status() -> dict:
    return {
        "state": "idle",
        "last_sync_time": None,
        "last_error": None,
        "remote_url": None,
        "branch": None,
        "git_available": False,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

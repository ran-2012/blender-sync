"""Background scheduler using bpy.app.timers."""

import os
from datetime import datetime, timezone

_timer_handle = None
_lock_check_timer = None


def register():
    """Register startup timer for remote check."""
    import bpy

    global _timer_handle
    # Schedule startup remote check after a short delay (let Blender finish loading)
    _timer_handle = bpy.app.timers.register(
        _startup_check,
        first_interval=3.0,
        persistent=True,
    )

    # Register timer for periodic sync
    _schedule_periodic()


def unregister():
    """Unregister timers."""
    import bpy
    global _timer_handle, _lock_check_timer

    if _timer_handle is not None:
        try:
            bpy.app.timers.unregister(_timer_handle)
        except (ValueError, AttributeError):
            pass
        _timer_handle = None

    if _lock_check_timer is not None:
        try:
            bpy.app.timers.unregister(_lock_check_timer)
        except (ValueError, AttributeError):
            pass
        _lock_check_timer = None


def _schedule_periodic():
    """Schedule periodic sync based on user preferences."""
    import bpy
    global _lock_check_timer

    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return

    interval = prefs.sync_interval
    if interval <= 0:
        return

    def _periodic_check():
        _background_sync()
        return interval  # Reschedule

    _lock_check_timer = bpy.app.timers.register(
        _periodic_check,
        first_interval=interval,
        persistent=True,
    )


def _startup_check():
    """Check remote at Blender startup (non-blocking)."""
    import bpy

    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return  # Timer cancelled

    if not prefs.startup_check_enabled:
        return  # Timer cancelled

    from . import preferences as pref_mod

    # Check Git availability
    git_ok = pref_mod.check_git_available()

    if not git_ok or not prefs.remote_url:
        return  # Timer done, nothing to do

    # Async fetch (this is a sync call but in a timer, so non-blocking)
    try:
        from .sync_service import SyncService
        svc = SyncService.from_bpy()
        svc.check_remote()

        # Auto-sync if enabled and remote has updates
        if prefs.auto_sync_enabled:
            svc.pull_remote()
    except Exception:
        pass  # Don't crash Blender on startup errors

    return  # One-shot timer done


def _background_sync():
    """Perform a background sync cycle."""
    from .sync_service import SyncService

    # Check lock
    if not _acquire_lock():
        return  # Another sync in progress

    try:
        svc = SyncService.from_bpy()
        svc.check_remote()

        import bpy
        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
        except (KeyError, AttributeError):
            _release_lock()
            return

        if prefs.auto_sync_enabled:
            svc.pull_remote()

    except Exception:
        pass
    finally:
        _release_lock()


# ------------------------------------------------------------------
# Lock file management
# ------------------------------------------------------------------

def _get_lock_path() -> str:
    from . import path_resolver
    data_dir = path_resolver.get_plugin_data_dir()
    runtime_dir = os.path.join(data_dir, "runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    return os.path.join(runtime_dir, "lock")


def _acquire_lock() -> bool:
    """Try to acquire the sync lock. Returns True if acquired."""
    lock_path = _get_lock_path()

    if os.path.exists(lock_path):
        # Check if the lock is stale
        try:
            with open(lock_path, "r") as f:
                content = f.read()
            # Parse PID from lock file
            for line in content.split("\n"):
                if line.startswith("pid="):
                    pid = int(line.split("=", 1)[1])
                    if not _is_process_running(pid):
                        # Stale lock, we can take it
                        _write_lock(lock_path)
                        return True
                    return False  # Active lock, can't acquire
        except (ValueError, OSError):
            # Corrupted lock, take it
            _write_lock(lock_path)
            return True

    _write_lock(lock_path)
    return True


def _write_lock(path: str):
    with open(path, "w") as f:
        f.write(f"pid={os.getpid()}\n")
        f.write(f"started={datetime.now(timezone.utc).isoformat()}\n")
        f.write("operation=sync\n")


def _release_lock():
    lock_path = _get_lock_path()
    try:
        os.remove(lock_path)
    except OSError:
        pass


def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running (cross-platform)."""
    try:
        import ctypes
        import ctypes.wintypes

        if os.name == 'nt':
            # Windows: check via kernel32
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            # Unix: send signal 0
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False

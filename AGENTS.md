# AGENTS.md — AI Agent Instructions

## Project Overview

Blender Sync is a Blender addon that syncs user settings, addons, and extensions across computers via Git. It runs inside Blender's Python environment (no `pip`, no threads touching `bpy`).

## Workspace Layout

```
blender_sync/          # The addon package (installed into Blender)
  __init__.py          # bl_info, register(), unregister()
  preferences.py       # AddonPreferences (UI config)
  panel.py             # 3D View sidebar panel
  operators.py         # Blender operators (modal timer + bg thread)
  sync_service.py      # Core sync orchestration (THREAD-SAFE, no bpy)
  git_adapter.py       # subprocess wrapper for system git
  path_resolver.py     # Cross-platform Blender path resolution
  snapshot.py          # Collect/apply files between Blender dir and staging
  manifest.py          # manifest.json + .gitignore/.gitattributes
  filters.py           # Plugin size threshold filtering
  ignores.py           # Default + user-defined ignore patterns (fnmatch)
  scheduler.py         # bpy.app.timers for startup check + periodic sync
  status_store.py      # JSON file status persistence
  bg_task.py           # BackgroundTask (daemon thread, no bpy)
  log.py               # Debug logging to file

docs/                  # Design docs
  research.md
  architecture.md
  implementation-plan.md

openspec/              # OpenSpec planning artifacts
scripts/
  prepare-test-win.ps1 # Windows dev setup (junction to Blender addons dir)
```

## Development Setup

```powershell
.\scripts\prepare-test-win.ps1   # Creates junction in Blender addons dir
```

Then in Blender: Edit → Preferences → Add-ons → enable "Blender Sync".

After code changes: disable then re-enable, or F3 → "Reload Scripts".

Clear stale bytecode:
```powershell
Get-ChildItem -Path "blender_sync" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

## Critical Constraints

1. **NO bpy in threads** — All sync methods in `SyncService` receive pre-collected preference dicts. Background thread runs `_run_sync()` which only touches filesystem and subprocess.
2. **NO bpy in subprocess callbacks** — Git commands run via `subprocess` only.
3. **Operators use modal + timer** — `_AsyncSyncOperator` base class: `execute()` collects prefs on main thread, launches `BackgroundTask`, `modal()` polls every 0.2s.
4. **`bpy.context` is volatile** — Never store references. Read from `context.preferences.addons[__package__]` fresh each time.

## Key Patterns

### Adding a new sync operation (network-capable)
- Subclass `_AsyncSyncOperator`, override `_run_sync(svc, prefs_data)`
- The base class handles thread launch, modal timer, and result reporting

### Adding a new sync operation (local-only, fast)
- Use plain `bpy.types.Operator`, call `SyncService.from_bpy()` in `execute()`

### Adding a new preference
- Add property to `BlenderSyncPreferences` in `preferences.py`
- Add to `_collect_prefs_dict()` in `sync_service.py`
- Access in sync methods via `self._prefs_data.get("key", default)`

## Git Operations

All git commands go through `GitAdapter`, using argument arrays (no shell strings):
```python
self._check_call("fetch", "origin", branch, timeout=120)
```

Errors raise `GitError(message, stderr, returncode)`.

## File Sync Flow

```
collect_to_staging()
  1. get_sync_target_paths() → list of (src_abs, rel_name)
  2. For each target: copy file or _sync_directory()
  3. _cleanup_stale_entries() → remove staging files not in source (prefix match)

apply_from_staging()
  Reverse: staging → Blender user directory
```

## Debug Logging

Enable **Debug Logging** in Preferences → **Open Log File** button in sidebar.

Or manually:
```
%APPDATA%\Blender Foundation\Blender\<version>\scripts\blender_sync_data\blender-sync-state\runtime\sync.log
```

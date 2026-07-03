"""Cross-platform path resolution for Blender user directories."""

import os

from . import ignores as ignores_mod


def get_blender_user_paths():
    """Return dict of sync-relevant Blender user paths.

    Returns dict with keys: config, scripts, extensions, addons, presets.
    Uses bpy.utils.user_resource() - no hardcoded paths.
    """
    import bpy

    config = bpy.utils.user_resource('CONFIG', path='', create=False)
    scripts = bpy.utils.user_resource('SCRIPTS', path='', create=False)

    # EXTENSIONS resource may not be available in all Blender versions.
    # Fallback: extensions/ is a sibling of config/ in the user dir.
    extensions = bpy.utils.user_resource('EXTENSIONS', path='', create=False)
    if not extensions or not os.path.isdir(extensions):
        # Derive from config path:  .../Blender/<version>/extensions
        parent = os.path.dirname(config)
        extensions = os.path.join(parent, "extensions")
        if not os.path.isdir(extensions):
            extensions = ""

    paths = {
        "config": config,
        "scripts": scripts,
        "extensions": extensions,
    }

    paths["addons"] = bpy.utils.user_resource('SCRIPTS', path='addons', create=False)
    paths["presets"] = bpy.utils.user_resource('SCRIPTS', path='presets', create=False)

    return paths


def get_plugin_data_dir():
    """Get the plugin's writable data directory.

    Creates blender-sync-state/ if it does not exist.
    """
    dir_path = _extension_path_user("blender-sync-state", create=True)
    return dir_path


def get_sync_target_paths(
    sync_recent_files: bool = False,
    ignore_patterns: list[str] = None,
):
    """Return list of (src_path, relative_name) tuples for files to sync.

    Args:
        sync_recent_files: Include recent-files.txt and recent-searches.txt.
        ignore_patterns: fnmatch patterns to exclude. None = use defaults.

    src_path: absolute path in Blender user dir
    relative_name: path relative to Blender user dir (used in staging repo)
    """
    if ignore_patterns is None:
        ignore_patterns = ignores_mod.get_default_ignores()

    user_paths = get_blender_user_paths()
    targets = []

    # ── Config files ──────────────────────────────────────────────
    config = user_paths["config"]

    # Always-included config files
    for fname in ignores_mod.DEFAULT_CONFIG_FILES:
        full = os.path.join(config, fname)
        if os.path.isfile(full) and not _is_ignored(fname, ignore_patterns):
            targets.append((full, f"config/{fname}"))

    # Optional config files
    if sync_recent_files:
        for fname in ignores_mod.OPTIONAL_CONFIG_FILES:
            full = os.path.join(config, fname)
            if os.path.isfile(full) and not _is_ignored(fname, ignore_patterns):
                targets.append((full, f"config/{fname}"))

    # Auto-discover other config files that are not in the known lists
    known_config = set(ignores_mod.DEFAULT_CONFIG_FILES + ignores_mod.OPTIONAL_CONFIG_FILES)
    if os.path.isdir(config):
        for fname in os.listdir(config):
            full = os.path.join(config, fname)
            if os.path.isfile(full) and fname not in known_config:
                if not _is_ignored(fname, ignore_patterns):
                    targets.append((full, f"config/{fname}"))

    # ── Scripts subdirectories ────────────────────────────────────
    for sub in ["presets", "addons"]:
        src = user_paths.get(sub)
        if src and os.path.isdir(src):
            if not _is_ignored(f"scripts/{sub}", ignore_patterns):
                targets.append((src, f"scripts/{sub}"))

    # ── Extensions ────────────────────────────────────────────────
    ext_dir = user_paths.get("extensions")
    if ext_dir and os.path.isdir(ext_dir):
        if not _is_ignored("extensions", ignore_patterns):
            targets.append((ext_dir, "extensions"))

    return targets


def _is_ignored(rel_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any ignore pattern."""
    import fnmatch

    # Normalize to forward slashes
    path = rel_path.replace("\\", "/")
    # Also check just the basename
    basename = os.path.basename(path)

    for pattern in patterns:
        p = pattern.replace("\\", "/")
        if fnmatch.fnmatch(path, p):
            return True
        if fnmatch.fnmatch(basename, p):
            return True
    return False


def _extension_path_user(subpath: str, create: bool = True):
    """Get a writable directory for this plugin.

    For traditional addons (not extensions), always uses
    SCRIPTS/blender_sync_data/ as the base data dir.
    """
    import os
    import bpy

    base = os.path.join(
        bpy.utils.user_resource('SCRIPTS', path='', create=True),
        "blender_sync_data",
    )

    target = os.path.join(base, subpath)
    if create and not os.path.exists(target):
        os.makedirs(target, exist_ok=True)

    return target

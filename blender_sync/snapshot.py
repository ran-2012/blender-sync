"""Snapshot: collect Blender user files into staging repo."""

import os
import shutil


def collect_to_staging(
    staging_repo_path: str,
    sync_recent_files: bool = False,
    incremental: bool = True,
    ignore_patterns: list[str] = None,
):
    """Collect Blender user files into the staging repo.

    Copies files from Blender user directories to staging repo,
    maintaining relative structure.

    Args:
        staging_repo_path: Path to the staging git repo.
        sync_recent_files: Whether to include recent-files.txt.
        incremental: If True, only copy changed files and remove stale ones.
    """
    from . import path_resolver

    targets = path_resolver.get_sync_target_paths(
        sync_recent_files, ignore_patterns=ignore_patterns,
    )

    # Track which staging paths we've written (for cleanup)
    written_paths = set()

    for src_path, rel_name in targets:
        dst_path = os.path.join(staging_repo_path, rel_name)
        written_paths.add(rel_name)

        if os.path.isfile(src_path):
            if incremental and os.path.exists(dst_path):
                if _files_identical(src_path, dst_path):
                    continue  # Skip unchanged files
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)

        elif os.path.isdir(src_path):
            os.makedirs(dst_path, exist_ok=True)
            _sync_directory(src_path, dst_path, incremental)

    # Cleanup: remove staging entries that no longer exist in source
    if incremental:
        _cleanup_stale_entries(staging_repo_path, written_paths)


def apply_from_staging(staging_repo_path: str):
    """Apply staging repo content back to Blender user directories.

    Reverse of collect_to_staging: copies files from staging to
    Blender user directories. Also removes files from user dir
    that were deleted in staging.
    """
    from . import path_resolver

    user_paths = path_resolver.get_blender_user_paths()

    # Map staging relative paths to actual user dirs
    mapping = {
        "config/": user_paths["config"],
        "scripts/presets/": user_paths["presets"],
        "scripts/addons/": user_paths["addons"],
        "extensions/": user_paths["extensions"],
    }

    for rel_prefix, user_dir in mapping.items():
        staging_prefix = os.path.join(staging_repo_path, rel_prefix)
        if not os.path.exists(staging_prefix):
            continue

        if os.path.isfile(staging_prefix):
            shutil.copy2(staging_prefix, user_dir)
        else:
            _sync_directory(staging_prefix, user_dir, incremental=False)

    # Handle individual config files
    config_staging = os.path.join(staging_repo_path, "config")
    config_user = user_paths.get("config")
    if os.path.isdir(config_staging) and config_user:
        for item in os.listdir(config_staging):
            src_item = os.path.join(config_staging, item)
            dst_item = os.path.join(config_user, item)
            if os.path.isfile(src_item):
                shutil.copy2(src_item, dst_item)
            elif os.path.isdir(src_item):
                if os.path.exists(dst_item):
                    shutil.rmtree(dst_item)
                shutil.copytree(src_item, dst_item, symlinks=False)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _files_identical(path1: str, path2: str) -> bool:
    """Check if two files have the same size and modification time."""
    try:
        s1 = os.stat(path1)
        s2 = os.stat(path2)
        return s1.st_size == s2.st_size and s1.st_mtime == s2.st_mtime
    except OSError:
        return False


def _sync_directory(src: str, dst: str, incremental: bool):
    """Sync a directory from src to dst.

    When incremental is True, only copy changed files and remove
    files in dst that don't exist in src.
    """
    src_items = set(os.listdir(src)) if os.path.isdir(src) else set()

    if os.path.isdir(dst):
        dst_items = set(os.listdir(dst))
        # Remove items in dst that are not in src
        for item in dst_items - src_items:
            item_path = os.path.join(dst, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

    for item in src_items:
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)

        if os.path.isfile(src_item):
            if incremental and os.path.exists(dst_item):
                if _files_identical(src_item, dst_item):
                    continue
            os.makedirs(os.path.dirname(dst_item), exist_ok=True)
            shutil.copy2(src_item, dst_item)
        elif os.path.isdir(src_item):
            if not os.path.exists(dst_item):
                shutil.copytree(src_item, dst_item, symlinks=False)
            else:
                _sync_directory(src_item, dst_item, incremental)


def _cleanup_stale_entries(staging_repo_path: str, written_paths: set):
    """Remove staging entries that are no longer in the source.

    Only cleans up known subdirectories to avoid accidental deletion.
    Uses prefix matching: any file/dir under a written_path is kept.
    """
    known_dirs = ["config", "scripts", "extensions"]
    for d in known_dirs:
        d_path = os.path.join(staging_repo_path, d)
        if not os.path.isdir(d_path):
            continue
        for root, dirs, files in os.walk(d_path, topdown=False):
            rel_root = os.path.relpath(root, staging_repo_path).replace("\\", "/")
            for fname in files:
                rel = f"{rel_root}/{fname}" if rel_root != "." else fname
                # Keep file if it's under any written path (prefix match)
                if _is_under_written_path(rel, written_paths):
                    continue
                try:
                    os.remove(os.path.join(root, fname))
                except OSError:
                    pass
            # Remove empty directories that aren't under a written parent
            if not os.listdir(root) and rel_root not in known_dirs:
                if not _is_under_written_path(rel_root, written_paths):
                    try:
                        os.rmdir(root)
                    except OSError:
                        pass


def _is_under_written_path(rel: str, written_paths: set) -> bool:
    """Check if a relative path starts with any written path (or is one)."""
    # Normalize path separators
    rel = rel.replace("\\", "/")
    for wp in written_paths:
        wp = wp.replace("\\", "/")
        if rel == wp or rel.startswith(wp + "/"):
            return True
    return False

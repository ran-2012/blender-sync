"""Manifest generation for snapshot metadata."""

import json
import hashlib
import os
from datetime import datetime, timezone


def generate_manifest(
    staging_repo_path: str,
    included_paths: list[str],
    excluded_paths: list[dict],
    plugin_size_threshold: int,
) -> dict:
    """Generate manifest.json content.

    Args:
        staging_repo_path: Path to the staging repo.
        included_paths: List of relative paths included in sync.
        excluded_paths: List of dicts with name, size, reason for skipped items.
        plugin_size_threshold: Threshold in MB.

    Returns:
        Dict ready to serialize as manifest.json.
    """
    import bpy

    manifest = {
        "blender_version": ".".join(str(v) for v in bpy.app.version),
        "os": _get_os_name(),
        "sync_schema_version": "1.0",
        "plugin_size_threshold_mb": plugin_size_threshold,
        "included": [],
        "excluded": excluded_paths,
        "last_exported": datetime.now(timezone.utc).isoformat(),
    }

    for rel_path in sorted(included_paths):
        full_path = os.path.join(staging_repo_path, rel_path)
        file_hash = _hash_file(full_path) if os.path.isfile(full_path) else None
        manifest["included"].append({
            "path": rel_path,
            "hash": file_hash,
        })

    return manifest


def write_manifest(staging_repo_path: str, manifest: dict) -> str:
    """Write manifest to staging repo. Returns the file path."""
    path = os.path.join(staging_repo_path, "manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return path


def write_gitignore(staging_repo_path: str) -> str:
    """Write .gitignore to staging repo. Returns the file path."""
    content = """\
# Blender Sync - .gitignore
# Exclude cache, logs, and temporary files

*.log
*.tmp
*.temp
__pycache__/
*.pyc
*.pyo
.DS_Store
Thumbs.db
"""
    path = os.path.join(staging_repo_path, ".gitignore")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def write_gitattributes(staging_repo_path: str) -> str:
    """Write .gitattributes to staging repo. Returns the file path."""
    content = """\
# Blender Sync - .gitattributes
# Force LF line endings for text files, mark binaries

* text=auto

*.blend binary
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.ttf binary
*.otf binary
*.zip binary
"""
    path = os.path.join(staging_repo_path, ".gitattributes")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _get_os_name() -> str:
    import platform
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Windows":
        return "windows"
    return system.lower()


def _hash_file(filepath: str, algorithm: str = "sha256") -> str:
    """Compute hash of a file."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

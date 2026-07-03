"""Filters for plugin size threshold and include/exclude patterns."""

import os


def get_dir_size_mb(dir_path: str) -> float:
    """Calculate total size of a directory in megabytes."""
    total = 0
    for dirpath, _, filenames in os.walk(dir_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)


def filter_plugins_by_size(
    base_dir: str,
    threshold_mb: int,
    whitelist: set[str] = None,
) -> tuple[list[str], list[dict]]:
    """Filter subdirectories by size threshold.

    Args:
        base_dir: Directory containing plugin subdirectories.
        threshold_mb: Maximum size in MB.
        whitelist: Set of directory names to always include.

    Returns:
        (included_names, excluded_info) where excluded_info is
        a list of dicts with name, size, reason.
    """
    if whitelist is None:
        whitelist = set()

    if not os.path.isdir(base_dir):
        return [], []

    included = []
    excluded = []

    for name in sorted(os.listdir(base_dir)):
        full = os.path.join(base_dir, name)
        if not os.path.isdir(full):
            continue

        size_mb = get_dir_size_mb(full)

        if name in whitelist or size_mb <= threshold_mb:
            included.append(name)
        else:
            excluded.append({
                "name": name,
                "size_mb": round(size_mb, 2),
                "reason": f"Exceeds size threshold ({size_mb:.1f} MB > {threshold_mb} MB)",
            })

    return included, excluded


def should_include_path(path: str, include_patterns: list[str], exclude_patterns: list[str]) -> bool:
    """Check if a path should be included based on patterns.

    Exclude patterns take priority over include patterns.
    Uses simple glob-style matching.
    """
    import fnmatch

    for pat in exclude_patterns:
        if pat and fnmatch.fnmatch(path, pat):
            return False

    if not include_patterns:
        return True

    for pat in include_patterns:
        if pat and fnmatch.fnmatch(path, pat):
            return True

    return False

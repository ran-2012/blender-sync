"""Ignore pattern management for Blender Sync.

Default ignore patterns are applied to both config files and
addon/extension directories. Users can add custom patterns
via Preferences.
"""

# Default patterns — applied to all sync targets
# Uses fnmatch / glob-style patterns relative to the sync root
DEFAULT_IGNORE_PATTERNS = [
    # Python cache
    "__pycache__/",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    # Blender extension cache / local
    ".cache/",
    ".cache/*",
    ".local/",
    ".local/*",
    ".blender_ext/",
    ".blender_ext/*",
    # Plugin's own data / dev links
    "blender_sync_data/",
    "blender_sync",
    "blender-sync-state/",
    "site_package/",
    # Platform-specific / machine-local
    "platform_support.txt",
    "compat.dat",
    # Common cache / temp
    "*.tmp",
    "*.temp",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
]

# Config files that are explicitly included by default
DEFAULT_CONFIG_FILES = [
    "userpref.blend",
    "startup.blend",
    "bookmarks.txt",
]

# Config files that are optional (user opts in)
OPTIONAL_CONFIG_FILES = [
    "recent-files.txt",
    "recent-searches.txt",
]


def get_default_ignores() -> list[str]:
    """Return a copy of the default ignore pattern list."""
    return list(DEFAULT_IGNORE_PATTERNS)


def parse_user_ignores(raw_text: str) -> list[str]:
    """Parse user-provided ignore patterns from a multi-line string.

    Empty lines and lines starting with # (comments) are skipped.
    Leading/trailing whitespace is stripped.
    """
    patterns = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def build_ignore_list(defaults: list[str], user_raw: str) -> list[str]:
    """Merge default and user ignore patterns. User patterns append to defaults."""
    user_patterns = parse_user_ignores(user_raw)
    combined = list(defaults)
    for p in user_patterns:
        if p not in combined:
            combined.append(p)
    return combined

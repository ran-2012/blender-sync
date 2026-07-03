"""AddonPreferences and Git availability detection."""

import bpy
import subprocess
from typing import Optional


GIT_VERSION: Optional[str] = None
"""Cached Git version string. None means not yet checked, empty means not found."""


def check_git_available() -> bool:
    """Check if Git is installed and accessible.

    Returns True if ``git --version`` succeeds, False otherwise.
    Caches the result in ``GIT_VERSION``.
    """
    global GIT_VERSION

    if GIT_VERSION is not None:
        return bool(GIT_VERSION)

    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            GIT_VERSION = result.stdout.strip()
            return True
        else:
            GIT_VERSION = ""
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        GIT_VERSION = ""
        return False


def register():
    """Register AddonPreferences."""
    bpy.utils.register_class(BlenderSyncPreferences)


def unregister():
    """Unregister AddonPreferences."""
    bpy.utils.unregister_class(BlenderSyncPreferences)


class BlenderSyncPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    remote_url: bpy.props.StringProperty(
        name="Remote URL",
        description="Git remote URL for syncing (e.g., git@github.com:user/blender-sync.git)",
        default="",
        subtype='NONE',
    )

    branch: bpy.props.StringProperty(
        name="Branch",
        description="Git branch to sync",
        default="main",
    )

    sync_interval: bpy.props.IntProperty(
        name="Sync Interval (seconds)",
        description="How often to check remote for changes. 0 = manual only",
        default=7200,
        min=0,
        soft_max=86400,
    )

    auto_sync_enabled: bpy.props.BoolProperty(
        name="Auto Sync",
        description="Automatically pull and apply remote changes when detected",
        default=False,
    )

    startup_check_enabled: bpy.props.BoolProperty(
        name="Startup Check",
        description="Check for remote changes when Blender starts",
        default=True,
    )

    conflict_policy: bpy.props.EnumProperty(
        name="Conflict Policy",
        description="Default behavior when conflicts are detected",
        items=[
            ('manual', "Manual", "Show conflict UI and let user decide per file"),
            ('local', "Prefer Local", "Keep local version, push to remote"),
            ('remote', "Prefer Remote", "Discard local, use remote version"),
        ],
        default='manual',
    )

    plugin_size_threshold: bpy.props.IntProperty(
        name="Plugin Size Threshold (MB)",
        description="Skip syncing individual addon/extension directories larger than this",
        default=50,
        min=1,
        soft_max=500,
    )

    sync_recent_files: bpy.props.BoolProperty(
        name="Sync Recent Files",
        description="Include config/recent-files.txt and recent-searches.txt in sync",
        default=False,
    )

    ignore_patterns: bpy.props.StringProperty(
        name="Ignore Patterns",
        description=(
            "Files/directories matching these patterns are excluded from sync. "
            "One pattern per line. Supports *, ?, [seq]. "
            "Changes take effect on next export."
        ),
        default="",
        subtype='NONE',
    )

    debug_logging: bpy.props.BoolProperty(
        name="Debug Logging",
        description="Write detailed sync logs to blender-sync-state/runtime/sync.log",
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        # Git status
        box = layout.box()
        box.label(text="Git Status", icon='TOOL_SETTINGS')
        if GIT_VERSION is None:
            check_git_available()

        if GIT_VERSION:
            box.label(text=f"Git: {GIT_VERSION}", icon='CHECKMARK')
        else:
            box.label(text="Git: Not Found", icon='ERROR')
            box.label(text="Please install Git to use Blender Sync.")
            return

        # Remote config
        box = layout.box()
        box.label(text="Remote Configuration", icon='URL')
        box.prop(self, "remote_url")
        box.prop(self, "branch")
        row = box.row()
        row.prop(self, "startup_check_enabled")
        row.prop(self, "auto_sync_enabled")

        # Sync settings
        box = layout.box()
        box.label(text="Sync Settings", icon='PREFERENCES')
        box.prop(self, "sync_interval")
        box.prop(self, "conflict_policy")
        box.prop(self, "plugin_size_threshold")
        box.prop(self, "sync_recent_files")

        # Ignore patterns
        box = layout.box()
        box.label(text="Ignore Patterns", icon='FILTER')
        box.label(text="One glob per line. Lines starting with # are comments.")
        box.prop(self, "ignore_patterns", text="")

        # Debug
        box = layout.box()
        box.label(text="Debug", icon='TOOL_SETTINGS')
        box.prop(self, "debug_logging")

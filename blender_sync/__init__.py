bl_info = {
    "name": "Blender Sync",
    "author": "Ran",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "3D View > Sidebar > Blender Sync",
    "description": "Sync Blender settings, addons, and presets across devices via Git",
    "category": "System",
}

import importlib
import sys
import os

# Ensure package path is available for imports
_package_dir = os.path.dirname(__file__)
if _package_dir not in sys.path:
    sys.path.insert(0, _package_dir)


def _reload_modules():
    """Reload all plugin modules for development convenience."""
    module_names = [
        "preferences",
        "operators",
        "panel",
        "scheduler",
        "sync_service",
        "git_adapter",
        "path_resolver",
        "snapshot",
        "manifest",
        "status_store",
        "filters",
        "ignores",
        "bg_task",
        "log",
    ]
    for name in module_names:
        if name in sys.modules:
            importlib.reload(sys.modules[name])


def register():
    """Register all plugin classes and start background scheduler."""
    _reload_modules()

    import bpy

    from . import preferences
    from . import operators
    from . import panel
    from . import scheduler

    preferences.register()
    operators.register()
    panel.register()
    scheduler.register()


def unregister():
    """Unregister all plugin classes and stop background scheduler."""
    import bpy

    from . import scheduler
    from . import panel
    from . import operators
    from . import preferences

    scheduler.unregister()
    panel.unregister()
    operators.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register()

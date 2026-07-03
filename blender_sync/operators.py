"""Operator definitions for Blender Sync actions.

Network-capable operators (SyncNow, CheckRemote, PushLocal, PullRemote, ResolveConflict)
use modal timers + background threads to avoid blocking the Blender UI.
"""

import bpy

from .bg_task import BackgroundTask


def register():
    bpy.utils.register_class(BLENDER_SYNC_OT_SyncNow)
    bpy.utils.register_class(BLENDER_SYNC_OT_CheckRemote)
    bpy.utils.register_class(BLENDER_SYNC_OT_PushLocal)
    bpy.utils.register_class(BLENDER_SYNC_OT_PullRemote)
    bpy.utils.register_class(BLENDER_SYNC_OT_ResolveConflict)
    bpy.utils.register_class(BLENDER_SYNC_OT_ViewHistory)
    bpy.utils.register_class(BLENDER_SYNC_OT_Rollback)
    bpy.utils.register_class(BLENDER_SYNC_OT_OpenLog)


def unregister():
    bpy.utils.unregister_class(BLENDER_SYNC_OT_OpenLog)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_Rollback)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_ViewHistory)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_ResolveConflict)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_PullRemote)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_PushLocal)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_CheckRemote)
    bpy.utils.unregister_class(BLENDER_SYNC_OT_SyncNow)


# ------------------------------------------------------------------
# Base class for async modal operators
# ------------------------------------------------------------------

class _AsyncSyncOperator(bpy.types.Operator):
    """Base for operators that run sync work in a background thread."""

    _timer = None
    _task = None
    _result = None
    _label = "Syncing"

    def modal(self, context, event):
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        if self._task is None:
            self.cancel(context)
            return {'CANCELLED'}

        if self._task.is_done:
            return self._finish(context)

        # Still running; update UI area to show progress
        if context.area:
            context.area.tag_redraw()
        return {'PASS_THROUGH'}

    def _finish(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None

        try:
            self._result = self._task.result()
        except Exception as e:
            self.report({'ERROR'}, str(e))
            self._task = None
            return {'CANCELLED'}

        self._task = None
        self._handle_result(context)
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}

    def _handle_result(self, context):
        """Override in subclass to handle the sync result."""
        if self._result:
            _report_result(self, self._result)

    def execute(self, context):
        # Collect prefs on main thread (bpy-safe)
        from .sync_service import SyncService, _collect_prefs_dict
        try:
            prefs = context.preferences.addons[__package__].preferences
            prefs_data = _collect_prefs_dict(prefs)
        except (KeyError, AttributeError):
            self.report({'ERROR'}, "Preferences not available")
            return {'CANCELLED'}

        if not prefs_data.get("remote_url"):
            self.report({'ERROR'}, "Remote URL not configured. Set it in Preferences.")
            return {'CANCELLED'}

        # Create sync service and launch background task
        svc = SyncService.from_prefs_dict(prefs_data)
        self._task = BackgroundTask(self._run_sync, svc, prefs_data)
        self._task.start()

        # Start modal timer for polling
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.2, window=context.window)
        wm.modal_handler_add(self)

        self.report({'INFO'}, f"{self._label} started...")
        return {'RUNNING_MODAL'}

    def _run_sync(self, svc, prefs_data) -> 'SyncResult':
        """Override in subclass — the actual sync work (runs in thread, no bpy)."""
        raise NotImplementedError

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        self._task = None


# ------------------------------------------------------------------
# Sync Now
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_SyncNow(_AsyncSyncOperator):
    bl_idname = "blender_sync.sync_now"
    bl_label = "Sync Now"
    bl_description = "Run full sync: export, commit, fetch, merge, push, apply"
    _label = "Sync"

    def _run_sync(self, svc, prefs_data):
        return svc.sync_now(trigger="manual")


# ------------------------------------------------------------------
# Check Remote
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_CheckRemote(_AsyncSyncOperator):
    bl_idname = "blender_sync.check_remote"
    bl_label = "Check Remote"
    bl_description = "Check remote for new changes"
    _label = "Remote check"

    def _run_sync(self, svc, prefs_data):
        return svc.check_remote()


# ------------------------------------------------------------------
# Push Local
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_PushLocal(_AsyncSyncOperator):
    bl_idname = "blender_sync.push_local"
    bl_label = "Push Local"
    bl_description = "Export and push local changes to remote"
    _label = "Push"

    def _run_sync(self, svc, prefs_data):
        return svc.push_local()


# ------------------------------------------------------------------
# Pull Remote
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_PullRemote(_AsyncSyncOperator):
    bl_idname = "blender_sync.pull_remote"
    bl_label = "Pull Remote"
    bl_description = "Pull remote changes and apply locally"
    _label = "Pull"

    def _run_sync(self, svc, prefs_data):
        return svc.pull_remote()


# ------------------------------------------------------------------
# Resolve Conflict
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_ResolveConflict(_AsyncSyncOperator):
    bl_idname = "blender_sync.resolve_conflict"
    bl_label = "Resolve Conflict"
    bl_description = "Resolve sync conflicts"
    _label = "Conflict resolution"

    strategy: bpy.props.EnumProperty(
        name="Strategy",
        items=[
            ('remote', "Overwrite Local (use remote)", "Discard local changes, use remote version"),
            ('local', "Overwrite Remote (use local)", "Keep local changes, force push to remote"),
        ],
        default='remote',
    )

    def _run_sync(self, svc, prefs_data):
        return svc.resolve_conflict(self.strategy)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, title="Resolve Conflict")


# ------------------------------------------------------------------
# View History (lightweight, no network — runs inline)
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_ViewHistory(bpy.types.Operator):
    bl_idname = "blender_sync.view_history"
    bl_label = "View History"
    bl_description = "View sync commit history"

    def execute(self, context):
        from .sync_service import SyncService
        svc = SyncService.from_bpy()
        commits = svc.get_history(limit=20)
        if not commits:
            self.report({'INFO'}, "No sync history found")
            return {'FINISHED'}
        for c in commits:
            self.report({'INFO'}, f"{c.sha}: {c.message}")
        return {'FINISHED'}


# ------------------------------------------------------------------
# Open Log
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_OpenLog(bpy.types.Operator):
    bl_idname = "blender_sync.open_log"
    bl_label = "Open Log"
    bl_description = "Open the sync.log file in the system text editor"

    def execute(self, context):
        import os
        import subprocess
        from . import path_resolver

        log_path = os.path.join(
            path_resolver.get_plugin_data_dir(),
            "runtime",
            "sync.log",
        )
        if not os.path.exists(log_path):
            self.report({'ERROR'}, f"Log file not found: {log_path}")
            return {'CANCELLED'}

        print(f"Blender Sync log: {log_path}")
        self.report({'INFO'}, f"Log: {log_path} (see System Console)")

        # Open in default text editor
        try:
            if os.name == 'nt':
                os.startfile(log_path)
            else:
                subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', log_path])
        except Exception as e:
            self.report({'ERROR'}, f"Cannot open log: {e}")

        return {'FINISHED'}


# ------------------------------------------------------------------
# Rollback (lightweight Git, no network — runs inline)
# ------------------------------------------------------------------

class BLENDER_SYNC_OT_Rollback(bpy.types.Operator):
    bl_idname = "blender_sync.rollback"
    bl_label = "Rollback"
    bl_description = "Rollback to a previous sync commit"

    commit: bpy.props.StringProperty(
        name="Commit SHA",
        description="Commit SHA to rollback to",
        default="",
    )

    def execute(self, context):
        if not self.commit:
            self.report({'ERROR'}, "Please enter a commit SHA")
            return {'CANCELLED'}
        from .sync_service import SyncService
        svc = SyncService.from_bpy()
        result = svc.rollback_to(self.commit, push=False)
        _report_result(self, result)
        return {'FINISHED'}

    def invoke(self, context, event):
        from .sync_service import SyncService
        svc = SyncService.from_bpy()
        commits = svc.get_history(limit=20)
        if not commits:
            self.report({'INFO'}, "No sync history found")
            return {'CANCELLED'}
        msg = "Recent commits:\n"
        for c in commits[:10]:
            msg += f"  {c.sha} - {c.message}\n"
        self.report({'INFO'}, msg.strip())
        return context.window_manager.invoke_props_dialog(self, title="Rollback")


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _report_result(op, result):
    """Report sync result to the Blender UI."""
    if result.success:
        op.report({'INFO'}, result.message)
    else:
        op.report({'ERROR'}, result.message)

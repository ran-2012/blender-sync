"""Panel UI for Blender Sync sidebar."""

import bpy


def register():
    bpy.utils.register_class(BLENDER_SYNC_PT_Panel)


def unregister():
    bpy.utils.unregister_class(BLENDER_SYNC_PT_Panel)


class BLENDER_SYNC_PT_Panel(bpy.types.Panel):
    bl_label = "Blender Sync"
    bl_idname = "BLENDER_SYNC_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Blender Sync"

    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[__package__].preferences

        # Status section
        box = layout.box()
        box.label(text="Status", icon='INFO')

        from .preferences import GIT_VERSION, check_git_available

        if GIT_VERSION is None:
            check_git_available()

        if not GIT_VERSION:
            box.label(text="Git not found", icon='ERROR')
            box.label(text="Install Git and restart Blender.")
            return

        box.label(text=f"Git: available", icon='CHECKMARK')

        if not prefs.remote_url:
            box.label(text="Remote not configured", icon='ERROR')
            box.label(text="Set remote URL in Preferences.")
            return

        # TODO: read from status_store when implemented
        box.label(text="Status: idle")
        box.label(text=f"Remote: {prefs.remote_url}")
        box.label(text=f"Branch: {prefs.branch}")

        # Actions section
        box = layout.box()
        box.label(text="Actions", icon='TOOL_SETTINGS')

        col = box.column(align=True)
        col.operator("blender_sync.sync_now", text="Sync Now", icon='FILE_REFRESH')
        col.operator("blender_sync.check_remote", text="Check Remote", icon='URL')
        col.operator("blender_sync.push_local", text="Push Local", icon='EXPORT')
        col.operator("blender_sync.pull_remote", text="Pull Remote", icon='IMPORT')

        # Advanced actions
        box = layout.box()
        box.label(text="Advanced", icon='MODIFIER')
        col = box.column(align=True)
        col.operator("blender_sync.resolve_conflict", text="Resolve Conflict", icon='ERROR')
        col.operator("blender_sync.view_history", text="View History", icon='TIME')
        col.operator("blender_sync.rollback", text="Rollback", icon='LOOP_BACK')

        # Debug
        if prefs.debug_logging:
            box = layout.box()
            box.label(text="Debug", icon='TOOL_SETTINGS')
            box.operator("blender_sync.open_log", text="Open Log File", icon='FILE_TEXT')

"""Sync service orchestrating the full sync workflow.

All sync methods are thread-safe (no bpy access).
Use ``SyncService.from_bpy()`` to create an instance from Blender context.
"""

import os
import shutil
import socket
from datetime import datetime, timezone

from . import git_adapter
from . import snapshot
from . import manifest as manifest_mod
from . import path_resolver
from . import status_store
from . import filters
from . import ignores as ignores_mod
from . import log as log_mod


class SyncResult:
    """Result of a sync operation."""

    def __init__(self, success: bool, state: str, message: str = "",
                 conflicts: list[str] = None):
        self.success = success
        self.state = state
        self.message = message
        self.conflicts = conflicts or []


def _collect_prefs_dict(prefs_obj) -> dict:
    """Extract preference values from a Blender prefs object into a plain dict."""
    return {
        "remote_url": prefs_obj.remote_url,
        "branch": prefs_obj.branch,
        "sync_interval": prefs_obj.sync_interval,
        "auto_sync_enabled": prefs_obj.auto_sync_enabled,
        "startup_check_enabled": prefs_obj.startup_check_enabled,
        "conflict_policy": prefs_obj.conflict_policy,
        "plugin_size_threshold": prefs_obj.plugin_size_threshold,
        "sync_recent_files": prefs_obj.sync_recent_files,
        "ignore_patterns": prefs_obj.ignore_patterns,
        "debug_logging": prefs_obj.debug_logging,
    }


class SyncService:
    """Orchestrates sync operations: collect, commit, fetch, merge, push, apply.

    Thread-safe: after construction with ``from_bpy()``, all methods avoid bpy.
    """

    def __init__(self, data_dir: str, repo_path: str, backup_dir: str,
                 prefs_data: dict = None):
        self._data_dir = data_dir
        self._repo_path = repo_path
        self._backup_dir = backup_dir
        self._prefs_data = prefs_data or {}
        self._git: git_adapter.GitAdapter | None = None

    @classmethod
    def from_bpy(cls):
        """Create SyncService from Blender context (call on main thread only)."""
        import bpy

        data_dir = path_resolver.get_plugin_data_dir()
        repo_path = os.path.join(data_dir, "repo")
        backup_dir = os.path.join(data_dir, "backups")

        try:
            prefs = bpy.context.preferences.addons[__package__].preferences
            prefs_data = _collect_prefs_dict(prefs)
        except (KeyError, AttributeError):
            prefs_data = {}

        return cls(data_dir, repo_path, backup_dir, prefs_data)

    @classmethod
    def from_prefs_dict(cls, prefs_data: dict):
        """Create SyncService from a pre-computed prefs dict (thread-safe)."""
        data_dir = path_resolver.get_plugin_data_dir()
        repo_path = os.path.join(data_dir, "repo")
        backup_dir = os.path.join(data_dir, "backups")
        return cls(data_dir, repo_path, backup_dir, prefs_data)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_git(self) -> git_adapter.GitAdapter:
        if self._git is None:
            os.makedirs(self._repo_path, exist_ok=True)
            self._git = git_adapter.GitAdapter(self._repo_path)
        return self._git

    def _update_status(self, **kwargs):
        status = status_store.read_status(self._data_dir)
        status.update(kwargs)
        status_store.write_status(self._data_dir, status)

    def _get_device_name(self) -> str:
        return socket.gethostname()

    def _remote_url(self) -> str:
        return self._prefs_data.get("remote_url", "")

    def _branch(self) -> str:
        return self._prefs_data.get("branch", "main")

    def _upstream(self) -> str:
        return f"origin/{self._branch()}"

    # ------------------------------------------------------------------
    # Core sync flow
    # ------------------------------------------------------------------

    def check_remote(self) -> SyncResult:
        git = self._ensure_git()
        remote = self._remote_url()
        if not remote:
            return SyncResult(False, "error", "Remote URL not configured")

        try:
            git.ensure_repo(remote, self._branch())
            git.fetch(branch=self._branch())
            rel = git.relation(self._branch(), self._upstream())

            if rel == git_adapter.BranchRelation.REMOTE_AHEAD:
                self._update_status(state="remote_update_available")
                return SyncResult(True, "remote_update_available", "Remote has new changes")
            elif rel == git_adapter.BranchRelation.DIVERGED:
                self._update_status(state="diverged")
                return SyncResult(True, "diverged", "Local and remote have diverged")
            elif rel == git_adapter.BranchRelation.LOCAL_AHEAD:
                self._update_status(state="local_ahead")
                return SyncResult(True, "local_ahead", "Local has unpushed changes")
            else:
                self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat())
                return SyncResult(True, "up_to_date", "Already up to date")
        except git_adapter.GitError as e:
            self._update_status(state="error", last_error=str(e))
            return SyncResult(False, "error", str(e))

    def sync_now(self, trigger: str = "manual") -> SyncResult:
        git = self._ensure_git()
        remote = self._remote_url()
        if not remote:
            return SyncResult(False, "error", "Remote URL not configured")

        try:
            branch = self._branch()
            upstream = self._upstream()

            self._update_status(state="exporting_snapshot")
            git.ensure_repo(remote, branch)
            self._export_snapshot()

            self._update_status(state="committing_local")
            device = self._get_device_name()
            timestamp = datetime.now(timezone.utc).isoformat()
            commit_sha = git.commit_all(f"Sync from {device} at {timestamp}")

            self._update_status(state="pulling_remote")
            git.fetch(branch=branch)
            rel = git.relation(branch, upstream)

            if rel == git_adapter.BranchRelation.UP_TO_DATE:
                if commit_sha:
                    git.push(branch=branch)
            elif rel == git_adapter.BranchRelation.LOCAL_AHEAD:
                git.push(branch=branch)
            elif rel == git_adapter.BranchRelation.REMOTE_AHEAD:
                mr = git.merge_remote(upstream)
                if not mr.success:
                    self._update_status(state="conflict", last_error="Merge conflict on pull")
                    return SyncResult(False, "conflict", "Merge conflict", mr.conflicts)
                self._apply_snapshot()
            elif rel == git_adapter.BranchRelation.DIVERGED:
                mr = git.merge_remote(upstream)
                if not mr.success:
                    self._update_status(state="conflict", last_error="Local and remote diverged")
                    return SyncResult(False, "conflict", "Diverged - manual resolution needed", mr.conflicts)
                git.push(branch=branch)
                self._apply_snapshot()

            self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat(), last_error=None)
            return SyncResult(True, "idle", "Sync completed")
        except git_adapter.GitError as e:
            self._update_status(state="error", last_error=str(e))
            return SyncResult(False, "error", str(e))

    def push_local(self) -> SyncResult:
        git = self._ensure_git()
        remote = self._remote_url()
        if not remote:
            return SyncResult(False, "error", "Remote not configured")

        try:
            branch = self._branch()
            git.ensure_repo(remote, branch)
            self._export_snapshot()

            device = self._get_device_name()
            timestamp = datetime.now(timezone.utc).isoformat()
            git.commit_all(f"Sync from {device} at {timestamp}")

            rel = git.relation(branch, self._upstream())
            if rel == git_adapter.BranchRelation.REMOTE_AHEAD:
                return SyncResult(False, "remote_ahead", "Remote has changes. Pull first or force push.")

            git.push(branch=branch)
            self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat())
            return SyncResult(True, "idle", "Push completed")
        except git_adapter.GitError as e:
            self._update_status(state="error", last_error=str(e))
            return SyncResult(False, "error", str(e))

    def pull_remote(self) -> SyncResult:
        git = self._ensure_git()
        remote = self._remote_url()
        if not remote:
            return SyncResult(False, "error", "Remote not configured")

        try:
            branch = self._branch()
            upstream = self._upstream()
            git.ensure_repo(remote, branch)

            if not self._prefs_data.get("auto_sync_enabled"):
                self._export_snapshot()
                git.commit_all(f"Auto-commit before pull from {self._get_device_name()}")

            git.fetch(branch=branch)
            rel = git.relation(branch, upstream)

            if rel == git_adapter.BranchRelation.UP_TO_DATE:
                return SyncResult(True, "idle", "Already up to date")
            elif rel == git_adapter.BranchRelation.LOCAL_AHEAD:
                return SyncResult(True, "local_ahead", "Local is ahead. Use push to upload.")
            elif rel == git_adapter.BranchRelation.REMOTE_AHEAD:
                self._create_backup()
                mr = git.merge_remote(upstream)
                if mr.success:
                    self._apply_snapshot()
                    self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat())
                    return SyncResult(True, "idle", "Pull and apply completed")
                else:
                    self._update_status(state="conflict")
                    return SyncResult(False, "conflict", "Merge conflict", mr.conflicts)
            else:
                return SyncResult(False, "diverged", "Branches diverged. Use sync to resolve.")
        except git_adapter.GitError as e:
            self._update_status(state="error", last_error=str(e))
            return SyncResult(False, "error", str(e))

    def resolve_conflict(self, strategy: str) -> SyncResult:
        git = self._ensure_git()
        branch = self._branch()
        upstream = self._upstream()

        try:
            if strategy == "remote":
                git.abort_merge()
                git.fetch(branch=branch)
                git._check_call("reset", "--hard", upstream)
                self._apply_snapshot()
                self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat())
                return SyncResult(True, "idle", "Local overwritten by remote")
            elif strategy == "local":
                self._export_snapshot()
                device = self._get_device_name()
                git.commit_all(f"Force sync from {device} at {datetime.now(timezone.utc).isoformat()}")
                git.force_push_with_lease(branch=branch)
                self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat())
                return SyncResult(True, "idle", "Remote overwritten by local")
            else:
                return SyncResult(False, "conflict", "Manual resolution required")
        except git_adapter.GitError as e:
            self._update_status(state="error", last_error=str(e))
            return SyncResult(False, "error", str(e))

    def rollback_to(self, commit: str, push: bool = False) -> SyncResult:
        git = self._ensure_git()
        try:
            self._create_backup()
            git.checkout_tree(commit)
            device = self._get_device_name()
            git.commit_all(f"Rollback to {commit} from {device} at {datetime.now(timezone.utc).isoformat()}")
            self._apply_snapshot()
            if push and self._remote_url():
                git.push(branch=self._branch())
            self._update_status(state="idle", last_sync_time=datetime.now(timezone.utc).isoformat())
            return SyncResult(True, "idle", f"Rolled back to {commit}")
        except git_adapter.GitError as e:
            self._update_status(state="error", last_error=str(e))
            return SyncResult(False, "error", str(e))

    def get_history(self, limit: int = 20) -> list:
        return self._ensure_git().log(limit=limit)

    def get_commit_detail(self, commit: str) -> str:
        return self._ensure_git().show_stat(commit)

    def get_rollback_preview(self, commit: str) -> str:
        return self._ensure_git().diff_summary(commit, "HEAD")

    # ------------------------------------------------------------------
    # Internal (uses path_resolver but no bpy context)
    # ------------------------------------------------------------------

    def _export_snapshot(self) -> None:
        # Init logging
        log_mod.init(self._data_dir)
        if self._prefs_data.get("debug_logging"):
            log_mod.enable()
        else:
            log_mod.disable()

        log_mod.header("EXPORT SNAPSHOT START")

        # Build ignore patterns from defaults + user config
        user_ignores_raw = self._prefs_data.get("ignore_patterns", "")
        ignore_patterns = ignores_mod.build_ignore_list(
            ignores_mod.get_default_ignores(),
            user_ignores_raw,
        )
        log_mod.info(f"ignore_patterns: {ignore_patterns}")

        # ── Log Blender user paths ────────────────────────────────
        user_paths = path_resolver.get_blender_user_paths()
        for key, val in user_paths.items():
            exists = os.path.isdir(val) or os.path.isfile(val) if val else False
            log_mod.info(f"user_path[{key}] = {val}  (exists={exists})")

        # ── Log sync targets ──────────────────────────────────────
        from . import path_resolver as pr
        targets = pr.get_sync_target_paths(
            sync_recent_files=self._prefs_data.get("sync_recent_files", False),
            ignore_patterns=ignore_patterns,
        )
        log_mod.info(f"sync targets count: {len(targets)}")
        for src, rel in targets:
            log_mod.info(f"  target: {rel}  <-  {src}")

        # ── Collect to staging ────────────────────────────────────
        snapshot.collect_to_staging(
            self._repo_path,
            sync_recent_files=self._prefs_data.get("sync_recent_files", False),
            ignore_patterns=ignore_patterns,
        )

        # ── Log staging repo contents ─────────────────────────────
        if os.path.isdir(self._repo_path):
            for root, dirs, files in os.walk(self._repo_path):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), self._repo_path)
                    log_mod.info(f"  staging: {rel}")

        # ── Plugin size filtering ─────────────────────────────────
        included = []
        excluded = []
        threshold = self._prefs_data.get("plugin_size_threshold", 50)

        for dir_key, rel_prefix in [("addons", "scripts/addons"), ("extensions", "extensions")]:
            src_dir = user_paths.get(dir_key)
            if src_dir and os.path.isdir(src_dir):
                inc, exc = filters.filter_plugins_by_size(src_dir, threshold)
                log_mod.info(f"filter_plugins[{dir_key}]: included={inc}, excluded={[e['name'] for e in exc]}")
                included.extend(f"{rel_prefix}/{name}" for name in inc)
                excluded.extend(exc)
            else:
                log_mod.warn(f"filter_plugins[{dir_key}]: src_dir missing or not a dir: {src_dir}")

        manifest_data = manifest_mod.generate_manifest(
            self._repo_path, included_paths=included,
            excluded_paths=excluded, plugin_size_threshold=threshold)
        manifest_mod.write_manifest(self._repo_path, manifest_data)
        manifest_mod.write_gitignore(self._repo_path)
        manifest_mod.write_gitattributes(self._repo_path)

        log_mod.header("EXPORT SNAPSHOT DONE")

    def _apply_snapshot(self) -> None:
        snapshot.apply_from_staging(self._repo_path)

    def _create_backup(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = os.path.join(self._backup_dir, timestamp)
        os.makedirs(backup_path, exist_ok=True)
        for src_path, rel_name in path_resolver.get_sync_target_paths():
            dst_path = os.path.join(backup_path, rel_name)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                if not os.path.exists(dst_path):
                    shutil.copytree(src_path, dst_path, symlinks=False)
        return backup_path


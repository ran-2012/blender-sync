"""Git adapter wrapping subprocess calls to system git."""

import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional


class GitError(Exception):
    """Raised when a git command fails."""

    def __init__(self, message: str, stderr: str = "", returncode: int = -1):
        super().__init__(message)
        self.stderr = stderr
        self.returncode = returncode


@dataclass
class GitStatus:
    is_dirty: bool = False
    changed_files: list[str] = field(default_factory=list)


@dataclass
class CommitInfo:
    sha: str
    message: str
    date: str
    author: str


class BranchRelation:
    UP_TO_DATE = "up_to_date"
    LOCAL_AHEAD = "local_ahead"
    REMOTE_AHEAD = "remote_ahead"
    DIVERGED = "diverged"


class MergeResult:
    """Result of a merge operation."""

    def __init__(self, success: bool, conflicts: list[str] = None, message: str = ""):
        self.success = success
        self.conflicts = conflicts or []
        self.message = message


class GitAdapter:
    """Encapsulates Git command execution via subprocess.

    All git commands use argument arrays (no shell string concatenation).
    """

    def __init__(self, repo_path: str):
        self._repo_path = repo_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, *args, timeout: int = 30, **kwargs) -> subprocess.CompletedProcess:
        """Run a git command. Returns CompletedProcess. Raises GitError on failure."""
        cmd = ["git"] + [str(a) for a in args]
        try:
            result = subprocess.run(
                cmd,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                **kwargs,
            )
            return result
        except subprocess.TimeoutExpired:
            raise GitError(
                f"Git command timed out: {' '.join(cmd)}",
                stderr="timeout",
                returncode=-1,
            )
        except FileNotFoundError:
            raise GitError(
                "Git executable not found. Is Git installed?",
                stderr="git not in PATH",
                returncode=-1,
            )

    def _check_call(self, *args, timeout: int = 30) -> str:
        """Run a git command, return stdout. Raise GitError on non-zero exit."""
        result = self._run(*args, timeout=timeout)
        if result.returncode != 0:
            raise GitError(
                f"Git command failed: git {' '.join(str(a) for a in args)}\n{result.stderr.strip()}",
                stderr=result.stderr.strip(),
                returncode=result.returncode,
            )
        return result.stdout.strip()

    def _get_commit_sha(self, ref: str = "HEAD") -> str:
        """Get the SHA of a ref."""
        return self._check_call("rev-parse", ref)

    # ------------------------------------------------------------------
    # Repo setup
    # ------------------------------------------------------------------

    def ensure_repo(self, remote_url: str, branch: str) -> None:
        """Initialize git repo if needed, configure remote and branch.

        Idempotent: safe to call on an already-initialized repo.
        """
        git_dir = os.path.join(self._repo_path, ".git")
        if not os.path.exists(git_dir):
            self._check_call("init")
            self._check_call("checkout", "-B", branch)

        # Ensure remote is set (add or update)
        try:
            current_url = self._check_call("remote", "get-url", "origin")
            if current_url != remote_url:
                self._check_call("remote", "set-url", "origin", remote_url)
        except GitError:
            self._check_call("remote", "add", "origin", remote_url)

        # Ensure we're on the correct branch
        try:
            current_branch = self._check_call("rev-parse", "--abbrev-ref", "HEAD")
            if current_branch != branch:
                self._check_call("checkout", "-B", branch)
        except GitError:
            self._check_call("checkout", "-B", branch)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> GitStatus:
        """Parse ``git status --porcelain`` into structured status."""
        try:
            output = self._check_call("status", "--porcelain")
        except GitError:
            return GitStatus()

        if not output:
            return GitStatus(is_dirty=False)

        changed = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            # porcelain format: XY filename (X=staging, Y=working tree)
            if len(line) >= 3:
                changed.append(line[3:].strip())

        return GitStatus(is_dirty=True, changed_files=changed)

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    def commit_all(self, message: str) -> Optional[str]:
        """Stage all changes and commit. Returns commit SHA or None if nothing to commit."""
        status = self.status()
        if not status.is_dirty:
            return None

        self._check_call("add", "-A")
        self._check_call("commit", "-m", message)
        return self._get_commit_sha()

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch(self, remote: str = "origin", branch: str = "main") -> None:
        """Fetch from remote. Raises GitError on failure (auth, network, etc.)."""
        try:
            self._check_call("fetch", remote, branch, timeout=120)
        except GitError as e:
            if "could not read" in e.stderr.lower() or "permission" in e.stderr.lower():
                raise GitError(
                    "Authentication failed. Check your Git credentials (SSH key or HTTPS token).",
                    stderr=e.stderr,
                    returncode=e.returncode,
                )
            elif "could not resolve" in e.stderr.lower() or "unable to connect" in e.stderr.lower():
                raise GitError(
                    "Remote is unreachable. Check your network and remote URL.",
                    stderr=e.stderr,
                    returncode=e.returncode,
                )
            raise

    # ------------------------------------------------------------------
    # Branch relation
    # ------------------------------------------------------------------

    def relation(self, branch: str, upstream: str) -> str:
        """Determine relationship between local branch and upstream.

        Returns one of: up_to_date, local_ahead, remote_ahead, diverged.
        """
        local_sha = self._get_commit_sha(branch)
        try:
            remote_sha = self._get_commit_sha(upstream)
        except GitError:
            # Remote branch doesn't exist yet → local is ahead
            return BranchRelation.LOCAL_AHEAD

        if local_sha == remote_sha:
            return BranchRelation.UP_TO_DATE

        # Check merge-base to determine relationship
        try:
            merge_base = self._check_call("merge-base", local_sha, remote_sha)
        except GitError:
            return BranchRelation.DIVERGED

        if merge_base == remote_sha:
            return BranchRelation.LOCAL_AHEAD
        elif merge_base == local_sha:
            return BranchRelation.REMOTE_AHEAD
        else:
            return BranchRelation.DIVERGED

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge_remote(self, upstream: str) -> MergeResult:
        """Merge remote branch into current HEAD.

        Returns MergeResult with success flag and conflict file list.
        """
        try:
            self._check_call("merge", upstream, "--no-edit")
            return MergeResult(success=True, message="Merge succeeded")
        except GitError as e:
            stderr = e.stderr
            if "CONFLICT" in stderr or "Automatic merge failed" in stderr:
                conflicts = self._list_conflict_files()
                return MergeResult(
                    success=False,
                    conflicts=conflicts,
                    message="Merge conflicts detected",
                )
            raise

    def abort_merge(self) -> None:
        """Abort an in-progress merge and return to pre-merge state."""
        self._check_call("merge", "--abort")

    def _list_conflict_files(self) -> list[str]:
        """List files with merge conflicts using git diff --name-only --diff-filter=U."""
        try:
            output = self._check_call("diff", "--name-only", "--diff-filter=U")
            return [f for f in output.split("\n") if f]
        except GitError:
            return []

    def is_binary(self, filepath: str) -> bool:
        """Check if a file is binary using git check-attr."""
        try:
            result = self._run("check-attr", "binary", "--", filepath)
            return "binary: set" in result.stdout
        except GitError:
            # Default to False for safety; user can still manually choose
            return False

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def push(self, remote: str = "origin", branch: str = "main") -> None:
        """Push local commits to remote."""
        self._check_call("push", remote, branch, timeout=120)

    def force_push_with_lease(self, remote: str = "origin", branch: str = "main") -> None:
        """Force push with lease (safer than --force).

        If remote has commits not known locally, push is rejected.
        """
        self._check_call("push", "--force-with-lease", remote, branch, timeout=120)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def log(self, limit: int = 20) -> list[CommitInfo]:
        """Get recent commit history."""
        fmt = "--format=%H||%s||%ai||%an"
        try:
            output = self._check_call("log", fmt, f"--max-count={limit}")
        except GitError:
            return []

        commits = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("||", 3)
            if len(parts) == 4:
                commits.append(CommitInfo(
                    sha=parts[0][:7],
                    message=parts[1],
                    date=parts[2],
                    author=parts[3],
                ))
        return commits

    def show_stat(self, commit: str) -> str:
        """Get ``git show --stat`` for a commit."""
        try:
            return self._check_call("show", "--stat", "--format=fuller", commit)
        except GitError as e:
            return f"Error: {e}"

    def diff_summary(self, old_commit: str, new_commit: str = "HEAD") -> str:
        """Get diff summary between two commits."""
        try:
            return self._check_call("diff", "--stat", old_commit, new_commit)
        except GitError as e:
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Checkout / Rollback
    # ------------------------------------------------------------------

    def checkout_tree(self, commit: str) -> None:
        """Checkout all files from a specific commit into the working tree.

        Does NOT move HEAD - this preserves history.
        Use for rollback: checkout old files, then commit as a new commit.
        """
        self._check_call("checkout", commit, "--", ".")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def has_remote(self) -> bool:
        """Check if the repo has a configured remote named 'origin'."""
        try:
            self._check_call("remote", "get-url", "origin")
            return True
        except GitError:
            return False

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        return self._check_call("rev-parse", "--abbrev-ref", "HEAD")

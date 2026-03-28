"""Git history extraction — log, blame, stats, contributors."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ContributorInfo:
    """Information about a contributor derived from git log."""

    name: str
    email: str
    recent_commits: int


@dataclass
class GitHistory:
    """Results of a git history scan."""

    is_git_repo: bool
    commit_count: int = 0
    contributors: list[ContributorInfo] = field(default_factory=list)
    head_commit: str | None = None
    recent_files_changed: list[str] = field(default_factory=list)


def _run(cmd: list[str], cwd: str) -> tuple[bool, str]:
    """Run a command and return (success, stdout)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0, result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, ""


def extract_git_history(repo_path: str) -> GitHistory:
    """Extract git history from a repository path.

    Returns an empty GitHistory if the path is not a git repo or
    if git is not available.  Never raises.
    """
    path = Path(repo_path)
    if not path.exists():
        return GitHistory(is_git_repo=False)

    cwd = str(path)

    # Verify it's a git repo
    ok, _ = _run(["git", "rev-parse", "--git-dir"], cwd)
    if not ok:
        return GitHistory(is_git_repo=False)

    # Get HEAD commit
    ok_head, head = _run(["git", "rev-parse", "--short", "HEAD"], cwd)
    head_commit = head.strip() if ok_head else None

    # Count commits
    ok_count, count_out = _run(["git", "rev-list", "--count", "HEAD"], cwd)
    commit_count = int(count_out.strip()) if ok_count and count_out.strip().isdigit() else 0

    # Get contributors (name + email + count)
    ok_log, log_out = _run(
        ["git", "log", "--format=%aN|%aE", "--no-merges", "-n", "1000"],
        cwd,
    )
    contributors: list[ContributorInfo] = []
    if ok_log and log_out:
        author_counts: dict[tuple[str, str], int] = {}
        for line in log_out.strip().splitlines():
            parts = line.split("|", 1)
            if len(parts) == 2:
                name, email = parts[0].strip(), parts[1].strip()
                key = (name, email)
                author_counts[key] = author_counts.get(key, 0) + 1

        contributors = [
            ContributorInfo(name=name, email=email, recent_commits=count)
            for (name, email), count in sorted(
                author_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

    # Get recently changed files
    ok_files, files_out = _run(
        ["git", "log", "--format=", "--name-only", "-n", "50", "--no-merges"],
        cwd,
    )
    recent_files: list[str] = []
    if ok_files and files_out:
        seen: set[str] = set()
        for f in files_out.strip().splitlines():
            f = f.strip()
            if f and f not in seen:
                seen.add(f)
                recent_files.append(f)

    return GitHistory(
        is_git_repo=True,
        commit_count=commit_count,
        contributors=contributors,
        head_commit=head_commit,
        recent_files_changed=recent_files[:50],
    )

"""Tests for the git history scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.scanners.git_history import extract_git_history, GitHistory


class TestExtractGitHistory:
    def test_returns_empty_when_not_git_repo(self, tmp_path: Path) -> None:
        """Returns a GitHistory with empty fields when path is not a git repo."""
        result = extract_git_history(str(tmp_path))
        assert isinstance(result, GitHistory)
        assert result.is_git_repo is False
        assert result.contributors == []
        assert result.commit_count == 0

    def test_returns_githistory_object(self, tmp_path: Path) -> None:
        """Always returns a GitHistory object, never raises."""
        result = extract_git_history(str(tmp_path))
        assert isinstance(result, GitHistory)

    def test_extracts_contributors_when_available(self, tmp_path: Path) -> None:
        """When a git repo is present, contributors list is populated."""
        import subprocess

        # Initialize a minimal git repo
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        (tmp_path / "file.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        result = extract_git_history(str(tmp_path))
        assert result.is_git_repo is True
        assert result.commit_count >= 1
        assert len(result.contributors) >= 1
        assert result.contributors[0].name == "Test User"

    def test_handles_non_existent_path_gracefully(self, tmp_path: Path) -> None:
        """Non-existent paths return empty GitHistory without raising."""
        non_existent = tmp_path / "does_not_exist"
        result = extract_git_history(str(non_existent))
        assert result.is_git_repo is False

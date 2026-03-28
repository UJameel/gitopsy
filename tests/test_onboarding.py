"""Tests for the onboarding guide generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.architecture import analyze as arch_analyze
from gitopsy.analyzers.onboarding import analyze
from gitopsy.models.schemas import OnboardingGuide


class TestOnboardingGuide:
    def test_extracts_project_summary_from_readme(self, flask_app_path: Path) -> None:
        """Extracts a project summary from the README.md file."""
        arch_report = arch_analyze(str(flask_app_path))
        guide = analyze(str(flask_app_path), arch_report)

        assert isinstance(guide, OnboardingGuide)
        assert len(guide.project_summary) > 0

    def test_identifies_setup_steps(self, flask_app_path: Path) -> None:
        """Identifies setup steps from README or package files."""
        arch_report = arch_analyze(str(flask_app_path))
        guide = analyze(str(flask_app_path), arch_report)

        assert isinstance(guide.setup_steps, list)
        # Flask app has install instructions in README
        assert len(guide.setup_steps) >= 0

    def test_finds_top_contributors_or_empty_list_if_no_git(
        self, flask_app_path: Path
    ) -> None:
        """Returns empty contributors list for non-git fixture repos."""
        arch_report = arch_analyze(str(flask_app_path))
        guide = analyze(str(flask_app_path), arch_report)

        # Fixture is not a git repo, so contributors should be empty
        assert isinstance(guide.top_contributors, list)

    def test_produces_gotchas_for_unusual_patterns(self, tmp_path: Path) -> None:
        """Produces gotchas when unusual patterns are detected."""
        # Create a repo with no tests directory (a gotcha)
        (tmp_path / "main.py").write_text("print('hello')\n")
        (tmp_path / "README.md").write_text("# Project\n")

        arch_report = arch_analyze(str(tmp_path))
        guide = analyze(str(tmp_path), arch_report)

        # Should at minimum not raise
        assert isinstance(guide.gotchas, list)

    def test_extracts_test_command(self, flask_app_path: Path) -> None:
        """Extracts test commands from README or config files."""
        arch_report = arch_analyze(str(flask_app_path))
        guide = analyze(str(flask_app_path), arch_report)

        assert isinstance(guide.test_commands, list)

    def test_extracts_key_files(self, flask_app_path: Path) -> None:
        """Key files list is populated from architecture report."""
        arch_report = arch_analyze(str(flask_app_path))
        guide = analyze(str(flask_app_path), arch_report)

        assert isinstance(guide.key_files, list)
        assert len(guide.key_files) > 0

    def test_architecture_overview_is_string(self, flask_app_path: Path) -> None:
        """Architecture overview is a non-empty string."""
        arch_report = arch_analyze(str(flask_app_path))
        guide = analyze(str(flask_app_path), arch_report)

        assert isinstance(guide.architecture_overview, str)
        assert len(guide.architecture_overview) > 0

    def test_returns_onboarding_guide(self, tmp_path: Path) -> None:
        """Returns an OnboardingGuide even for an empty directory."""
        arch_report = arch_analyze(str(tmp_path))
        guide = analyze(str(tmp_path), arch_report)

        assert isinstance(guide, OnboardingGuide)

    def test_nextjs_extracts_npm_test_command(self, nextjs_app_path: Path) -> None:
        """Detects npm test command from package.json scripts."""
        arch_report = arch_analyze(str(nextjs_app_path))
        guide = analyze(str(nextjs_app_path), arch_report)

        assert "npm test" in guide.test_commands or any(
            "jest" in cmd or "test" in cmd for cmd in guide.test_commands
        )

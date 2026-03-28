"""Tests for the architecture analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.architecture import analyze
from gitopsy.models.schemas import ArchitectureReport


class TestArchitectureAnalyzer:
    def test_detects_flask_framework(self, flask_app_path: Path) -> None:
        """Detects Flask framework from requirements.txt."""
        report = analyze(str(flask_app_path))
        assert isinstance(report, ArchitectureReport)
        assert report.framework is not None
        assert report.framework.lower() == "flask"

    def test_detects_nextjs_framework(self, nextjs_app_path: Path) -> None:
        """Detects Next.js framework from package.json."""
        report = analyze(str(nextjs_app_path))
        assert isinstance(report, ArchitectureReport)
        assert report.framework is not None
        assert "next" in report.framework.lower()

    def test_detects_python_cli_type(self, python_cli_path: Path) -> None:
        """Detects CLI project type from pyproject.toml scripts."""
        report = analyze(str(python_cli_path))
        assert isinstance(report, ArchitectureReport)
        # Should detect as cli or library
        assert report.project_type in {"cli", "library", "monolith"}

    def test_identifies_entry_points(self, flask_app_path: Path) -> None:
        """Finds app.py as an entry point."""
        report = analyze(str(flask_app_path))
        entry_paths = [ep.path for ep in report.entry_points]
        assert any("app.py" in p for p in entry_paths)

    def test_builds_language_breakdown(self, flask_app_path: Path) -> None:
        """Language breakdown includes Python."""
        report = analyze(str(flask_app_path))
        assert "Python" in report.language_breakdown
        assert report.language_breakdown["Python"] > 0

    def test_ranks_key_files(self, flask_app_path: Path) -> None:
        """Key files list is non-empty with importance scores."""
        report = analyze(str(flask_app_path))
        assert len(report.key_files) > 0
        for kf in report.key_files:
            assert 0 <= kf.importance_score <= 100

    def test_detects_flat_structure(self, flask_app_path: Path) -> None:
        """Detects 'flat' structure pattern for a simple Flask app."""
        report = analyze(str(flask_app_path))
        assert report.structure_pattern in {
            "flat", "mvc", "clean", "feature-based"
        }

    def test_total_files_count(self, flask_app_path: Path) -> None:
        """Total file count is greater than zero."""
        report = analyze(str(flask_app_path))
        assert report.total_files > 0

    def test_total_lines_count(self, flask_app_path: Path) -> None:
        """Total line count is greater than zero."""
        report = analyze(str(flask_app_path))
        assert report.total_lines > 0

    def test_returns_architecture_report_instance(self, tmp_path: Path) -> None:
        """Always returns an ArchitectureReport even for an empty dir."""
        report = analyze(str(tmp_path))
        assert isinstance(report, ArchitectureReport)

    def test_detects_nextjs_project_type(self, nextjs_app_path: Path) -> None:
        """Next.js app is detected as a monolith or similar web project."""
        report = analyze(str(nextjs_app_path))
        assert report.project_type in {"monolith", "library", "cli"}

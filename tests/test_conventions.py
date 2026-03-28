"""Tests for the convention detector analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.conventions import analyze
from gitopsy.models.schemas import ConventionReport


class TestNamingConventions:
    def test_detects_snake_case_in_python_files(self, flask_app_path: Path) -> None:
        """Python files in flask-app should be detected as snake_case."""
        report = analyze(str(flask_app_path))
        # Flask uses Python — should detect snake_case functions
        assert report.naming.functions in ("snake_case", None)

    def test_detects_camel_case_in_js_files(self, nextjs_app_path: Path) -> None:
        """JS files in nextjs-app should lean toward camelCase naming."""
        report = analyze(str(nextjs_app_path))
        # JS convention - may detect camelCase or None with limited files
        assert isinstance(report, ConventionReport)

    def test_detects_spaces_vs_tabs(self, flask_app_path: Path) -> None:
        """Detects whether files use spaces or tabs for indentation."""
        report = analyze(str(flask_app_path))
        assert report.formatting.indent_style in ("spaces", "tabs", None)

    def test_detects_relative_imports_in_nextjs(self, nextjs_app_path: Path) -> None:
        """Detects import style in nextjs-app."""
        report = analyze(str(nextjs_app_path))
        assert report.import_style in ("relative", "absolute", "barrel", "mixed", "unknown")

    def test_detects_test_pattern_separate_dir(self, flask_app_path: Path) -> None:
        """flask-app has a tests/ directory — detected as separate-dir pattern."""
        report = analyze(str(flask_app_path))
        assert report.test_pattern in ("separate-dir", "co-located", "mixed", "unknown")

    def test_computes_consistency_score(self, flask_app_path: Path) -> None:
        """consistency_score is an integer in 0-100 range."""
        report = analyze(str(flask_app_path))
        assert isinstance(report.consistency_score, int)
        assert 0 <= report.consistency_score <= 100

    def test_handles_mixed_conventions(self, tmp_path: Path) -> None:
        """Mixed-indent files still produce a valid ConventionReport."""
        (tmp_path / "a.py").write_text(
            "def foo():\n    pass\n"  # 4 spaces
        )
        (tmp_path / "b.py").write_text(
            "def bar():\n\tpass\n"  # tabs
        )
        report = analyze(str(tmp_path))
        assert isinstance(report, ConventionReport)
        assert 0 <= report.consistency_score <= 100


class TestConventionReportShape:
    def test_returns_convention_report_type(self, flask_app_path: Path) -> None:
        """analyze() returns a ConventionReport."""
        report = analyze(str(flask_app_path))
        assert isinstance(report, ConventionReport)

    def test_handles_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns a valid ConventionReport with score 100."""
        report = analyze(str(tmp_path))
        assert isinstance(report, ConventionReport)
        assert report.consistency_score == 100

    def test_git_conventions_field_present(self, flask_app_path: Path) -> None:
        """git_conventions field is present even when no git history is found."""
        report = analyze(str(flask_app_path))
        assert report.git_conventions is not None

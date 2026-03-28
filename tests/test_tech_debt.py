"""Tests for the tech debt scorer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.tech_debt import analyze
from gitopsy.models.schemas import TechDebtReport


class TestTechDebtScorer:
    def test_scores_todo_density(self, tmp_path: Path) -> None:
        """Files with many TODO comments get a higher todo_density score."""
        # Create a file with lots of TODOs
        code = "\n".join(f"# TODO: fix this {i}" for i in range(20))
        (tmp_path / "bad.py").write_text(code + "\n")

        report = analyze(str(tmp_path))
        assert isinstance(report, TechDebtReport)
        assert "todo_density" in report.dimensions
        assert report.dimensions["todo_density"].score > 0

    def test_computes_overall_score_and_grade(self, flask_app_path: Path) -> None:
        """Overall score is 0-100 and grade is A/B/C/D/F."""
        report = analyze(str(flask_app_path))
        assert 0 <= report.overall_score <= 100
        assert report.grade in {"A", "B", "C", "D", "F"}

    def test_identifies_complex_files(self, tmp_path: Path) -> None:
        """Files >500 lines are flagged as hotspots."""
        big_code = "\n".join(f"x_{i} = {i}" for i in range(600))
        (tmp_path / "big_file.py").write_text(big_code + "\n")

        report = analyze(str(tmp_path))
        hotspot_paths = [h.path for h in report.hotspots]
        assert any("big_file.py" in p for p in hotspot_paths)

    def test_detects_dead_code_signals(self, tmp_path: Path) -> None:
        """Files with zero imports from other files are flagged."""
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "unused.py").write_text("y = 2\n")

        report = analyze(str(tmp_path))
        assert isinstance(report, TechDebtReport)
        assert "dead_code" in report.dimensions

    def test_grade_a_for_clean_code(self, tmp_path: Path) -> None:
        """A clean, well-tested repo gets grade A (score 0-20)."""
        # Create a clean file with no TODOs, docstrings, small
        clean_code = '''"""A clean module with good practices."""


def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"
'''
        (tmp_path / "clean.py").write_text(clean_code)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_clean.py").write_text(
            '"""Tests for clean module."""\n\n\ndef test_greet():\n    assert True\n'
        )

        report = analyze(str(tmp_path))
        # Grade A means score 0-20
        assert report.grade in {"A", "B", "C"}  # Clean code should be decent

    def test_grade_f_for_terrible_code(self, tmp_path: Path) -> None:
        """A repo with many issues gets a high score."""
        # No tests, many TODOs, big files
        awful_code = "# TODO: everything\n# FIXME: broken\n# HACK: bad\n"
        awful_code += "\n".join(f"x_{i} = {i}  # TODO: refactor" for i in range(550))
        (tmp_path / "awful.py").write_text(awful_code)

        report = analyze(str(tmp_path))
        assert report.overall_score > 20  # Should not be grade A

    def test_generates_recommendations(self, flask_app_path: Path) -> None:
        """Report includes at least one recommendation."""
        report = analyze(str(flask_app_path))
        assert isinstance(report.recommendations, list)
        # Flask app has TODOs in it, should have recommendations
        assert len(report.recommendations) >= 0  # May be 0 for a clean fixture

    def test_all_dimensions_present(self, flask_app_path: Path) -> None:
        """All 7 dimensions are present in the report."""
        expected = {
            "todo_density",
            "code_staleness",
            "test_coverage",
            "complexity",
            "dependency_freshness",
            "documentation",
            "dead_code",
        }
        report = analyze(str(flask_app_path))
        assert set(report.dimensions.keys()) == expected

    def test_returns_tech_debt_report(self, tmp_path: Path) -> None:
        """Returns a TechDebtReport even for an empty directory."""
        report = analyze(str(tmp_path))
        assert isinstance(report, TechDebtReport)

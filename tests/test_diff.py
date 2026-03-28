"""Tests for the diff/comparison mode."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from gitopsy.models.schemas import (
    ArchitectureReport,
    ConventionReport,
    DepEdge,
    DimensionScore,
    FormattingRules,
    GitConventions,
    GitopsyReport,
    Hotspot,
    KeyFile,
    Layer,
    NamingConventions,
    SecurityFinding,
    SecurityReport,
    TechDebtReport,
)
from gitopsy.report.diff import compare, render_diff


def _make_report(
    project_name: str = "test-project",
    grade: str = "B",
    score: int = 70,
    findings: list[SecurityFinding] | None = None,
    key_files: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> GitopsyReport:
    """Factory for minimal GitopsyReport objects."""
    debt = TechDebtReport(
        overall_score=score,
        grade=grade,
        dimensions={
            "complexity": DimensionScore(name="complexity", score=70, detail="ok", weight=1.0)
        },
        hotspots=[],
        recommendations=recommendations or [],
        trend_data=None,
    )

    kf_list = [
        KeyFile(path=p, role="key", importance_score=80)
        for p in (key_files or [])
    ]
    arch = ArchitectureReport(
        project_type="library",
        framework=None,
        structure_pattern="flat",
        entry_points=[],
        layers=[],
        key_files=kf_list,
        internal_deps=[],
        language_breakdown={"python": 100.0},
        total_files=10,
        total_lines=500,
    )

    security = SecurityReport(
        risk_level="low",
        findings=findings or [],
        secrets_found=0,
        env_files_in_git=[],
        exposed_ports=[],
        auth_pattern=None,
        recommendations=[],
    )

    return GitopsyReport(
        repo_path="/tmp/test",
        project_name=project_name,
        generated_at="2026-01-01T00:00:00Z",
        git_commit=None,
        tech_debt=debt,
        architecture=arch,
        security=security,
    )


class TestDiffDetectsGradeImprovement:
    def test_diff_detects_grade_improvement(self):
        old = _make_report(grade="C", score=55)
        new = _make_report(grade="B", score=72)
        result = compare(old, new)
        assert result["grade_change"] == ("C", "B")
        assert result["grade_improved"] is True

    def test_diff_detects_grade_regression(self):
        old = _make_report(grade="A", score=90)
        new = _make_report(grade="B", score=75)
        result = compare(old, new)
        assert result["grade_change"] == ("A", "B")
        assert result["grade_improved"] is False

    def test_diff_detects_score_change(self):
        old = _make_report(grade="B", score=60)
        new = _make_report(grade="B", score=80)
        result = compare(old, new)
        assert result["score_change"] == 20

    def test_diff_detects_score_decrease(self):
        old = _make_report(grade="A", score=90)
        new = _make_report(grade="B", score=70)
        result = compare(old, new)
        assert result["score_change"] == -20

    def test_diff_unchanged_grade(self):
        old = _make_report(grade="B", score=75)
        new = _make_report(grade="B", score=75)
        result = compare(old, new)
        assert result["grade_improved"] is False
        assert result["score_change"] == 0


class TestDiffDetectsNewSecurityFindings:
    def _finding(self, severity: str = "high", category: str = "secrets", line: int = 10) -> SecurityFinding:
        return SecurityFinding(
            severity=severity,
            category=category,
            file="app.py",
            line=line,
            description="hardcoded secret",
        )

    def test_diff_detects_new_security_findings(self):
        old = _make_report(findings=[])
        new = _make_report(findings=[self._finding()])
        result = compare(old, new)
        assert len(result["new_findings"]) == 1
        assert result["new_findings"][0]["severity"] == "high"

    def test_diff_detects_resolved_findings(self):
        f = self._finding()
        old = _make_report(findings=[f])
        new = _make_report(findings=[])
        result = compare(old, new)
        assert len(result["resolved_findings"]) == 1
        assert len(result["new_findings"]) == 0

    def test_diff_no_finding_change(self):
        f = self._finding()
        old = _make_report(findings=[f])
        new = _make_report(findings=[f])
        result = compare(old, new)
        assert len(result["new_findings"]) == 0
        assert len(result["resolved_findings"]) == 0

    def test_diff_finding_keys_include_expected_fields(self):
        old = _make_report(findings=[])
        new = _make_report(findings=[self._finding(severity="critical", category="injection")])
        result = compare(old, new)
        f = result["new_findings"][0]
        assert "severity" in f
        assert "category" in f
        assert "file" in f
        assert "description" in f


class TestDiffRendersHTML:
    def test_diff_renders_html(self):
        old = _make_report(grade="C", score=55)
        new = _make_report(grade="B", score=72)
        diff = compare(old, new)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            out_path = f.name
        render_diff(diff, out_path)
        content = Path(out_path).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Gitopsy Diff Report" in content
        assert "B" in content
        assert "C" in content

    def test_diff_html_contains_grade_section(self):
        old = _make_report(grade="D", score=40)
        new = _make_report(grade="C", score=60)
        diff = compare(old, new)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            out_path = f.name
        render_diff(diff, out_path)
        content = Path(out_path).read_text(encoding="utf-8")
        assert "Health Grade" in content
        assert "improved" in content.lower()

    def test_diff_html_contains_security_section(self):
        finding = SecurityFinding(
            severity="high", category="secrets", file="config.py", line=5,
            description="hardcoded password"
        )
        old = _make_report(findings=[])
        new = _make_report(findings=[finding])
        diff = compare(old, new)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            out_path = f.name
        render_diff(diff, out_path)
        content = Path(out_path).read_text(encoding="utf-8")
        assert "Security Findings" in content
        assert "hardcoded password" in content


class TestDiffKeyFiles:
    def test_diff_detects_new_files(self):
        old = _make_report(key_files=["app.py"])
        new = _make_report(key_files=["app.py", "routes.py"])
        result = compare(old, new)
        assert "routes.py" in result["new_files"]

    def test_diff_detects_deleted_files(self):
        old = _make_report(key_files=["app.py", "legacy.py"])
        new = _make_report(key_files=["app.py"])
        result = compare(old, new)
        assert "legacy.py" in result["deleted_files"]


class TestDiffRecommendations:
    def test_diff_detects_new_recommendations(self):
        old = _make_report(recommendations=["Add tests"])
        new = _make_report(recommendations=["Add tests", "Fix complexity"])
        result = compare(old, new)
        assert "Fix complexity" in result["new_recommendations"]

    def test_diff_detects_resolved_recommendations(self):
        old = _make_report(recommendations=["Add tests", "Fix complexity"])
        new = _make_report(recommendations=["Fix complexity"])
        result = compare(old, new)
        assert "Add tests" in result["resolved_recommendations"]

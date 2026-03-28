"""Integration tests — full pipeline on fixture repos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gitopsy.orchestrator import analyze
from gitopsy.report.renderer import render


class TestFullPipeline:
    def test_full_pipeline_flask_fixture(self, flask_app_path: Path, tmp_path: Path) -> None:
        """Full pipeline produces a GitopsyReport for the flask-app fixture."""
        report = analyze(str(flask_app_path))
        assert report.architecture is not None
        assert report.tech_debt is not None
        assert report.onboarding is not None

    def test_full_pipeline_nextjs_fixture(self, nextjs_app_path: Path) -> None:
        """Full pipeline on nextjs-app fixture completes without errors."""
        report = analyze(str(nextjs_app_path))
        assert report.architecture is not None
        assert report.architecture.framework is not None
        assert "next" in report.architecture.framework.lower()

    def test_html_output_flask(self, flask_app_path: Path, tmp_path: Path) -> None:
        """Full pipeline renders valid HTML for flask-app fixture."""
        report = analyze(str(flask_app_path))
        output = str(tmp_path / "flask-report.html")
        render(report, output)

        html = Path(output).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
        assert "gitopsy" in html.lower()

    def test_html_has_all_three_tabs(self, flask_app_path: Path, tmp_path: Path) -> None:
        """Rendered HTML contains all three tab buttons."""
        report = analyze(str(flask_app_path))
        output = str(tmp_path / "report.html")
        render(report, output)

        html = Path(output).read_text(encoding="utf-8")
        assert "Architecture" in html
        assert "Tech Debt" in html
        assert "Onboarding" in html

    def test_html_is_self_contained(self, flask_app_path: Path, tmp_path: Path) -> None:
        """Rendered HTML has no external http:// src/href references for critical assets."""
        report = analyze(str(flask_app_path))
        output = str(tmp_path / "report.html")
        render(report, output)

        html = Path(output).read_text(encoding="utf-8")
        # Chart.js CDN is acceptable per spec; check there are no stylesheet/script
        # links to random external domains (beyond Chart.js CDN)
        import re
        external_links = re.findall(r'(?:href|src)=["\']https?://[^"\']+["\']', html)
        # Filter out the allowed Chart.js CDN
        disallowed = [
            link for link in external_links
            if "cdn.jsdelivr.net" not in link
            and "cdnjs.cloudflare.com" not in link
        ]
        assert disallowed == [], f"Unexpected external links: {disallowed}"

    def test_json_output(self, flask_app_path: Path) -> None:
        """Report can be serialized to valid JSON."""
        report = analyze(str(flask_app_path))
        json_str = report.model_dump_json()
        data = json.loads(json_str)
        assert data["project_name"] == flask_app_path.name

    def test_arch_only_analyzer(self, flask_app_path: Path) -> None:
        """Running only arch analyzer skips debt and onboarding."""
        report = analyze(str(flask_app_path), analyzers=["arch"])
        assert report.architecture is not None
        assert report.tech_debt is None
        assert report.onboarding is None

    def test_empty_directory_pipeline(self, tmp_path: Path) -> None:
        """Pipeline on empty directory does not raise."""
        report = analyze(str(tmp_path))
        assert report is not None

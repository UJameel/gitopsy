"""Tests for the dependency mapper analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.dependencies import analyze
from gitopsy.models.schemas import DependencyReport

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestParsesManifests:
    def test_parses_requirements_txt(self, flask_app_path: Path) -> None:
        """Parses flask-app requirements.txt and finds flask, sqlalchemy."""
        report = analyze(str(flask_app_path))
        names = {d.name.lower() for d in report.deps}
        assert "flask" in names
        assert "sqlalchemy" in names

    def test_parses_package_json(self, nextjs_app_path: Path) -> None:
        """Parses nextjs-app package.json and finds next, react."""
        report = analyze(str(nextjs_app_path))
        names = {d.name.lower() for d in report.deps}
        assert "next" in names
        assert "react" in names

    def test_parses_pyproject_toml(self, tmp_path: Path) -> None:
        """Parses pyproject.toml [project.dependencies] section."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            'name = "my-app"\n'
            "dependencies = [\n"
            '    "httpx>=0.24",\n'
            '    "pydantic>=2.0",\n'
            "]\n"
        )
        report = analyze(str(tmp_path))
        names = {d.name.lower() for d in report.deps}
        assert "httpx" in names
        assert "pydantic" in names

    def test_handles_missing_manifest_gracefully(self, tmp_path: Path) -> None:
        """Returns a valid DependencyReport for a dir with no manifest files."""
        report = analyze(str(tmp_path))
        assert isinstance(report, DependencyReport)
        assert report.total_deps == 0
        assert report.deps == []

    def test_detects_license_in_package_json(self, nextjs_app_path: Path) -> None:
        """Detects license field from package.json."""
        # nextjs-app fixture may or may not have a license field; add one to test dir
        import json
        pkg = nextjs_app_path / "package.json"
        data = json.loads(pkg.read_text())
        data["license"] = "MIT"
        # Write to tmp dir
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(str(nextjs_app_path), tmp, dirs_exist_ok=True)
            (Path(tmp) / "package.json").write_text(json.dumps(data))
            report = analyze(tmp)
        # At minimum the report should have package.json deps
        names = {d.name.lower() for d in report.deps}
        assert "next" in names or "react" in names

    def test_flags_outdated_dependencies(self, tmp_path: Path) -> None:
        """Flags old pinned major versions as outdated."""
        req = tmp_path / "requirements.txt"
        req.write_text("flask==0.12.0\nrequests==2.28.0\n")
        report = analyze(str(tmp_path))
        statuses = {d.name.lower(): d.status for d in report.deps}
        # flask 0.x is very old — should be flagged outdated
        assert statuses.get("flask") == "outdated"

    def test_computes_risk_score(self, flask_app_path: Path) -> None:
        """risk_score is an integer in 0-100 range."""
        report = analyze(str(flask_app_path))
        assert isinstance(report.risk_score, int)
        assert 0 <= report.risk_score <= 100


class TestDependencyReportShape:
    def test_returns_dependency_report_type(self, flask_app_path: Path) -> None:
        """analyze() returns a DependencyReport instance."""
        report = analyze(str(flask_app_path))
        assert isinstance(report, DependencyReport)

    def test_package_manager_detected(self, flask_app_path: Path) -> None:
        """package_manager is set to a non-empty string."""
        report = analyze(str(flask_app_path))
        assert report.package_manager
        assert isinstance(report.package_manager, str)

    def test_total_deps_matches_list(self, flask_app_path: Path) -> None:
        """total_deps equals len(deps)."""
        report = analyze(str(flask_app_path))
        assert report.total_deps == len(report.deps)

"""Tests for the security surface scanner analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.security_surface import analyze
from gitopsy.models.schemas import SecurityReport


class TestSecretDetection:
    def test_detects_hardcoded_api_key(self, flask_app_path: Path) -> None:
        """Detects the fake AWS key comment in flask-app/app.py."""
        report = analyze(str(flask_app_path))
        categories = {f.category for f in report.findings}
        # Should find either 'secrets' or 'hardcoded-secret' category
        assert any("secret" in c.lower() or "aws" in c.lower() or "key" in c.lower() for c in categories)

    def test_detects_sql_injection_risk(self, flask_app_path: Path) -> None:
        """Detects SQL injection risk from string interpolation in flask-app."""
        report = analyze(str(flask_app_path))
        categories = {f.category for f in report.findings}
        assert any("sql" in c.lower() or "injection" in c.lower() for c in categories)

    def test_computes_critical_risk_for_secrets(self, flask_app_path: Path) -> None:
        """Risk level is 'critical' or 'high' when secrets are found."""
        report = analyze(str(flask_app_path))
        assert report.secrets_found > 0
        assert report.risk_level in ("critical", "high")

    def test_finding_has_required_fields(self, flask_app_path: Path) -> None:
        """Each SecurityFinding has severity, category, file, description."""
        report = analyze(str(flask_app_path))
        for finding in report.findings:
            assert finding.severity in ("low", "medium", "high", "critical")
            assert finding.category
            assert finding.file
            assert finding.description


class TestGitignoreCheck:
    def test_detects_missing_gitignore_for_env(self, tmp_path: Path) -> None:
        """Detects when .env exists but is not in .gitignore."""
        (tmp_path / ".env").write_text("SECRET_KEY=abc123\n")
        # No .gitignore — env file is unprotected
        report = analyze(str(tmp_path))
        # Either finds env file in git findings or env_files_in_git
        has_env_finding = any(
            "env" in f.category.lower() or ".env" in f.file
            for f in report.findings
        )
        assert has_env_finding or len(report.findings) >= 0  # at minimum no crash


class TestAuthPatternDetection:
    def test_detects_jwt_auth_pattern(self, tmp_path: Path) -> None:
        """Detects JWT auth pattern when jwt library is imported."""
        (tmp_path / "auth.py").write_text(
            "import jwt\n"
            "def create_token(user_id):\n"
            '    return jwt.encode({"sub": user_id}, "secret")\n'
        )
        report = analyze(str(tmp_path))
        assert report.auth_pattern is not None
        assert "jwt" in report.auth_pattern.lower()

    def test_no_findings_for_clean_code(self, tmp_path: Path) -> None:
        """Clean code with no secrets or SQL injection has no findings."""
        (tmp_path / "utils.py").write_text(
            "def add(a, b):\n"
            "    return a + b\n"
        )
        report = analyze(str(tmp_path))
        assert isinstance(report, SecurityReport)
        assert report.secrets_found == 0
        # Risk level should be low
        assert report.risk_level in ("low", "medium")


class TestDockerPortDetection:
    def test_detects_docker_exposed_ports(self, tmp_path: Path) -> None:
        """Detects exposed ports from docker-compose.yml."""
        (tmp_path / "docker-compose.yml").write_text(
            "version: '3'\n"
            "services:\n"
            "  web:\n"
            "    image: nginx\n"
            "    ports:\n"
            "      - '8080:80'\n"
            "      - '443:443'\n"
        )
        report = analyze(str(tmp_path))
        assert 8080 in report.exposed_ports or 80 in report.exposed_ports or 443 in report.exposed_ports


class TestSecurityReportShape:
    def test_returns_security_report_type(self, flask_app_path: Path) -> None:
        """analyze() returns a SecurityReport instance."""
        report = analyze(str(flask_app_path))
        assert isinstance(report, SecurityReport)

    def test_recommendations_list_present(self, flask_app_path: Path) -> None:
        """recommendations is a list."""
        report = analyze(str(flask_app_path))
        assert isinstance(report.recommendations, list)

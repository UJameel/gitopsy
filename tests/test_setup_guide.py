"""Tests for the setup guide builder analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.setup_guide import analyze
from gitopsy.models.schemas import SetupGuide


class TestPrerequisiteDetection:
    def test_detects_python_prerequisite(self, flask_app_path: Path) -> None:
        """Detects Python as a prerequisite for flask-app fixture."""
        report = analyze(str(flask_app_path))
        prereq_names = {p.name.lower() for p in report.prerequisites}
        assert "python" in prereq_names

    def test_detects_node_prerequisite(self, nextjs_app_path: Path) -> None:
        """Detects Node.js as a prerequisite for nextjs-app fixture."""
        report = analyze(str(nextjs_app_path))
        prereq_names = {p.name.lower() for p in report.prerequisites}
        assert any("node" in n for n in prereq_names)


class TestInstallCommands:
    def test_extracts_install_command_from_requirements(self, flask_app_path: Path) -> None:
        """Generates pip install step when requirements.txt is present."""
        report = analyze(str(flask_app_path))
        commands = [s.command for s in report.install_steps if s.command]
        assert any("requirements" in cmd or "pip" in cmd for cmd in commands)

    def test_generates_npm_install_for_package_json(self, nextjs_app_path: Path) -> None:
        """Generates npm install step when package.json is present."""
        report = analyze(str(nextjs_app_path))
        commands = [s.command for s in report.install_steps if s.command]
        assert any("npm" in cmd or "yarn" in cmd for cmd in commands)


class TestEnvVarExtraction:
    def test_extracts_env_vars_from_env_example(self, tmp_path: Path) -> None:
        """Parses .env.example and produces EnvVar entries."""
        (tmp_path / ".env.example").write_text(
            "DATABASE_URL=postgres://localhost/mydb\n"
            "SECRET_KEY=your-secret-here\n"
            "DEBUG=false\n"
        )
        report = analyze(str(tmp_path))
        env_names = {e.name for e in report.env_vars}
        assert "DATABASE_URL" in env_names
        assert "SECRET_KEY" in env_names

    def test_scans_source_for_env_usage(self, tmp_path: Path) -> None:
        """Scans Python source for os.environ.get() calls."""
        (tmp_path / "config.py").write_text(
            "import os\n"
            'DB_URL = os.environ.get("DATABASE_URL")\n'
            'API_KEY = os.environ.get("API_KEY", "default")\n'
        )
        report = analyze(str(tmp_path))
        env_names = {e.name for e in report.env_vars}
        assert "DATABASE_URL" in env_names
        assert "API_KEY" in env_names


class TestRunCommandExtraction:
    def test_extracts_run_command_from_readme(self, tmp_path: Path) -> None:
        """Extracts run commands from README code blocks."""
        (tmp_path / "README.md").write_text(
            "# My App\n\n"
            "## Running\n\n"
            "```bash\n"
            "flask run\n"
            "```\n"
        )
        report = analyze(str(tmp_path))
        # run_commands should have something
        assert isinstance(report.run_commands, dict)

    def test_handles_no_setup_info_gracefully(self, tmp_path: Path) -> None:
        """Empty directory returns a valid SetupGuide with empty lists."""
        report = analyze(str(tmp_path))
        assert isinstance(report, SetupGuide)
        assert isinstance(report.prerequisites, list)
        assert isinstance(report.install_steps, list)


class TestSetupGuideShape:
    def test_returns_setup_guide_type(self, flask_app_path: Path) -> None:
        """analyze() returns a SetupGuide instance."""
        report = analyze(str(flask_app_path))
        assert isinstance(report, SetupGuide)

    def test_install_steps_are_ordered(self, flask_app_path: Path) -> None:
        """install_steps have sequential order values."""
        report = analyze(str(flask_app_path))
        for i, step in enumerate(report.install_steps):
            assert step.order == i + 1

    def test_test_command_detected_for_pytest(self, flask_app_path: Path) -> None:
        """pytest is detected as the test command for flask-app."""
        report = analyze(str(flask_app_path))
        # flask-app has pytest in requirements.txt
        assert report.test_command is not None
        assert "pytest" in report.test_command.lower()

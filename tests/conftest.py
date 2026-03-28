"""Shared pytest fixtures for Gitopsy tests."""

from __future__ import annotations

from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def flask_app_path() -> Path:
    """Path to the flask-app fixture repo."""
    return FIXTURES_DIR / "flask-app"


@pytest.fixture()
def nextjs_app_path() -> Path:
    """Path to the nextjs-app fixture repo."""
    return FIXTURES_DIR / "nextjs-app"


@pytest.fixture()
def python_cli_path() -> Path:
    """Path to the python-cli fixture repo."""
    return FIXTURES_DIR / "python-cli"


@pytest.fixture()
def tmp_empty_dir(tmp_path: Path) -> Path:
    """An empty temporary directory."""
    return tmp_path


@pytest.fixture()
def tmp_dir_with_files(tmp_path: Path) -> Path:
    """A temporary directory with some files for testing."""
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "utils.py").write_text("def helper(): pass\n")
    (tmp_path / "README.md").write_text("# Test\n")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "module.py").write_text("x = 1\n")
    return tmp_path

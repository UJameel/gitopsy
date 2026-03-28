"""Tests for the API extractor analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.analyzers.api_extractor import analyze
from gitopsy.models.schemas import APIReport


class TestFlaskRoutes:
    def test_extracts_flask_routes(self, flask_app_path: Path) -> None:
        """Extracts /health, /users, /users/<id> from flask-app fixture."""
        report = analyze(str(flask_app_path))
        paths = {ep.path for ep in report.endpoints}
        assert "/health" in paths
        assert "/users" in paths
        # /users/<int:user_id> or similar
        assert any("users" in p and ("<" in p or "{" in p) for p in paths)

    def test_flask_methods_detected(self, flask_app_path: Path) -> None:
        """GET and POST methods are both detected for /users endpoint."""
        report = analyze(str(flask_app_path))
        users_endpoints = [ep for ep in report.endpoints if ep.path == "/users"]
        methods = {ep.method for ep in users_endpoints}
        assert "GET" in methods
        assert "POST" in methods


class TestNextjsApiRoutes:
    def test_extracts_nextjs_api_routes(self, nextjs_app_path: Path) -> None:
        """Extracts pages/api/users.js and pages/api/products.js as routes."""
        report = analyze(str(nextjs_app_path))
        paths = {ep.path for ep in report.endpoints}
        assert any("users" in p for p in paths)
        assert any("products" in p for p in paths)

    def test_nextjs_route_path_format(self, nextjs_app_path: Path) -> None:
        """Next.js routes include /api/ prefix."""
        report = analyze(str(nextjs_app_path))
        paths = {ep.path for ep in report.endpoints}
        assert any(p.startswith("/api/") for p in paths)


class TestClickCommands:
    def test_extracts_click_commands(self, python_cli_path: Path) -> None:
        """Extracts greet, status, process commands from python-cli fixture."""
        report = analyze(str(python_cli_path))
        assert report.cli_commands is not None
        names = {cmd.name for cmd in report.cli_commands}
        assert "greet" in names
        assert "status" in names
        assert "process" in names

    def test_api_type_is_cli(self, python_cli_path: Path) -> None:
        """python-cli fixture is detected as 'cli' api_type."""
        report = analyze(str(python_cli_path))
        assert report.api_type in ("cli", "mixed")


class TestFastapiRoutes:
    def test_extracts_fastapi_routes(self, tmp_path: Path) -> None:
        """Extracts FastAPI @app.get / @app.post routes."""
        (tmp_path / "main.py").write_text(
            'from fastapi import FastAPI\n'
            'app = FastAPI()\n'
            '\n'
            '@app.get("/items")\n'
            'def list_items():\n'
            '    return []\n'
            '\n'
            '@app.post("/items")\n'
            'def create_item():\n'
            '    return {}\n'
            '\n'
            '@app.get("/items/{item_id}")\n'
            'def get_item(item_id: int):\n'
            '    return {}\n'
        )
        report = analyze(str(tmp_path))
        paths = {ep.path for ep in report.endpoints}
        assert "/items" in paths
        methods = {ep.method for ep in report.endpoints if ep.path == "/items"}
        assert "GET" in methods
        assert "POST" in methods


class TestEdgeCases:
    def test_handles_no_api_gracefully(self, tmp_path: Path) -> None:
        """Dir with no API files returns an APIReport with zero endpoints."""
        (tmp_path / "utils.py").write_text("def helper(): pass\n")
        report = analyze(str(tmp_path))
        assert isinstance(report, APIReport)
        assert report.total_routes == 0

    def test_counts_undocumented_routes(self, flask_app_path: Path) -> None:
        """undocumented_routes count is set (some routes may lack docstrings)."""
        report = analyze(str(flask_app_path))
        assert isinstance(report.undocumented_routes, int)
        assert report.undocumented_routes >= 0

    def test_returns_api_report_type(self, flask_app_path: Path) -> None:
        """analyze() returns an APIReport instance."""
        report = analyze(str(flask_app_path))
        assert isinstance(report, APIReport)

    def test_total_routes_matches_endpoints(self, flask_app_path: Path) -> None:
        """total_routes equals len(endpoints)."""
        report = analyze(str(flask_app_path))
        assert report.total_routes == len(report.endpoints)

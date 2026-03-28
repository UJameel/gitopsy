"""Tests for the language detection scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.scanners.language_detect import detect_languages


class TestDetectLanguages:
    def test_detects_python_files(self, tmp_path: Path) -> None:
        """Python files are correctly detected."""
        (tmp_path / "main.py").write_text("print('hello')\n")
        (tmp_path / "utils.py").write_text("def helper(): pass\n")

        result = detect_languages(str(tmp_path))
        assert "Python" in result
        assert result["Python"]["file_count"] == 2

    def test_detects_javascript_files(self, tmp_path: Path) -> None:
        """JavaScript files are correctly detected."""
        (tmp_path / "app.js").write_text("console.log('hi');\n")
        (tmp_path / "index.js").write_text("module.exports = {};\n")

        result = detect_languages(str(tmp_path))
        assert "JavaScript" in result
        assert result["JavaScript"]["file_count"] == 2

    def test_returns_percentage_breakdown(self, tmp_path: Path) -> None:
        """Returns percentage alongside file/line counts."""
        (tmp_path / "main.py").write_text("x = 1\ny = 2\n")
        (tmp_path / "app.js").write_text("var x = 1;\n")

        result = detect_languages(str(tmp_path))
        percentages = [v["percentage"] for v in result.values()]
        assert abs(sum(percentages) - 100.0) < 0.1, "Percentages should sum to ~100"

    def test_handles_unknown_extensions(self, tmp_path: Path) -> None:
        """Unknown file extensions are grouped as 'Other' or skipped."""
        (tmp_path / "file.xyz123").write_text("mystery\n")
        (tmp_path / "main.py").write_text("x = 1\n")

        # Should not raise
        result = detect_languages(str(tmp_path))
        assert "Python" in result

    def test_empty_directory_returns_empty(self, tmp_empty_dir: Path) -> None:
        """Empty directory returns empty dict."""
        result = detect_languages(str(tmp_empty_dir))
        assert result == {}

    def test_detects_typescript_files(self, tmp_path: Path) -> None:
        """TypeScript files are detected separately from JavaScript."""
        (tmp_path / "app.ts").write_text("const x: number = 1;\n")
        (tmp_path / "app.js").write_text("var x = 1;\n")

        result = detect_languages(str(tmp_path))
        assert "TypeScript" in result
        assert "JavaScript" in result

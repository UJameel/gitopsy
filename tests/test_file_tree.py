"""Tests for the file tree scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitopsy.scanners.file_tree import walk_tree, FileInfo


class TestWalkTree:
    def test_walks_directory_returns_files(self, tmp_dir_with_files: Path) -> None:
        """walk_tree returns a non-empty list of FileInfo objects."""
        files = walk_tree(str(tmp_dir_with_files))
        assert len(files) > 0
        assert all(isinstance(f, FileInfo) for f in files)

    def test_respects_gitignore(self, tmp_path: Path) -> None:
        """Files matching .gitignore patterns are excluded."""
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        (tmp_path / "ignored.py").write_text("x = 1\n")
        (tmp_path / "kept.py").write_text("y = 2\n")

        files = walk_tree(str(tmp_path))
        paths = [f.path for f in files]

        assert not any("ignored.py" in p for p in paths)
        assert any("kept.py" in p for p in paths)

    def test_skips_hidden_dirs(self, tmp_path: Path) -> None:
        """Hidden directories like node_modules, .git, __pycache__ are skipped."""
        for hidden in ["node_modules", ".git", "__pycache__"]:
            d = tmp_path / hidden
            d.mkdir()
            (d / "file.js").write_text("x = 1;\n")
        (tmp_path / "real.py").write_text("x = 1\n")

        files = walk_tree(str(tmp_path))
        paths = [f.path for f in files]

        assert all("node_modules" not in p for p in paths)
        assert all(".git" not in p for p in paths)
        assert all("__pycache__" not in p for p in paths)
        assert any("real.py" in p for p in paths)

    def test_returns_relative_paths(self, tmp_dir_with_files: Path) -> None:
        """Returned paths are relative to the repo root."""
        files = walk_tree(str(tmp_dir_with_files))
        for f in files:
            assert not Path(f.path).is_absolute(), f"Expected relative path, got: {f.path}"

    def test_handles_empty_directory(self, tmp_empty_dir: Path) -> None:
        """walk_tree on an empty directory returns an empty list."""
        files = walk_tree(str(tmp_empty_dir))
        assert files == []

    def test_includes_size_metadata(self, tmp_dir_with_files: Path) -> None:
        """Each FileInfo has size_bytes set."""
        files = walk_tree(str(tmp_dir_with_files))
        for f in files:
            assert f.size_bytes >= 0

    def test_skips_large_files(self, tmp_path: Path) -> None:
        """Files larger than 1MB are skipped."""
        large = tmp_path / "large.bin"
        large.write_bytes(b"x" * (1024 * 1024 + 1))
        small = tmp_path / "small.py"
        small.write_text("x = 1\n")

        files = walk_tree(str(tmp_path))
        paths = [f.path for f in files]

        assert not any("large.bin" in p for p in paths)
        assert any("small.py" in p for p in paths)

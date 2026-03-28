"""File tree walker that respects .gitignore and skips binary/large files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# Directories that are always skipped regardless of .gitignore
_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        "env",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".eggs",
        "*.egg-info",
        ".DS_Store",
        ".idea",
        ".vscode",
        "coverage",
        ".coverage",
        "htmlcov",
    }
)

# Max file size: 1 MB
_MAX_SIZE_BYTES: int = 1024 * 1024

# Known binary extensions to skip
_BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".webp",
        ".mp4",
        ".mp3",
        ".wav",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".o",
        ".a",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".pyc",
        ".pyo",
        ".pyd",
        ".db",
        ".sqlite",
        ".sqlite3",
    }
)


@dataclass
class FileInfo:
    """Metadata about a single file in the tree."""

    path: str          # Relative to the repo root
    size_bytes: int
    language: str | None = None
    line_count: int = 0


def _load_gitignore_patterns(root: Path) -> list[str]:
    """Load patterns from .gitignore in root, if present."""
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _matches_gitignore(relative_path: str, patterns: list[str]) -> bool:
    """Return True if a relative path matches any gitignore pattern."""
    import fnmatch

    parts = Path(relative_path).parts
    name = Path(relative_path).name

    for pattern in patterns:
        # Strip leading /
        clean = pattern.lstrip("/")
        # Match against the filename alone, or the full relative path
        if fnmatch.fnmatch(name, clean):
            return True
        if fnmatch.fnmatch(relative_path, clean):
            return True
        # Match any path segment
        if not "/" in clean:
            for part in parts:
                if fnmatch.fnmatch(part, clean):
                    return True
    return False


def walk_tree(repo_path: str) -> list[FileInfo]:
    """Walk a directory tree and return FileInfo objects for all relevant files.

    - Respects .gitignore patterns in the root
    - Skips known non-source directories (node_modules, .git, __pycache__, etc.)
    - Skips binary files and files > 1MB
    - Returns relative paths
    """
    root = Path(repo_path).resolve()
    if not root.is_dir():
        return []

    gitignore_patterns = _load_gitignore_patterns(root)
    result: list[FileInfo] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        # Prune directories in-place (modifies os.walk traversal)
        dirnames[:] = [
            d
            for d in dirnames
            if d not in _SKIP_DIRS
            and not d.startswith(".")
            and not _matches_gitignore(
                str((current / d).relative_to(root)), gitignore_patterns
            )
        ]

        for filename in filenames:
            abs_file = current / filename
            try:
                relative = str(abs_file.relative_to(root))
            except ValueError:
                continue

            # Skip gitignore matches
            if _matches_gitignore(relative, gitignore_patterns):
                continue

            # Skip binary extensions
            suffix = abs_file.suffix.lower()
            if suffix in _BINARY_EXTENSIONS:
                continue

            # Skip large files
            try:
                size = abs_file.stat().st_size
            except OSError:
                continue
            if size > _MAX_SIZE_BYTES:
                continue

            # Count lines
            try:
                text = abs_file.read_text(encoding="utf-8", errors="replace")
                line_count = text.count("\n")
                if text and not text.endswith("\n"):
                    line_count += 1
            except OSError:
                line_count = 0

            result.append(
                FileInfo(
                    path=relative,
                    size_bytes=size,
                    line_count=line_count,
                )
            )

    return result

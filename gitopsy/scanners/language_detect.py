"""Language detection from file extensions and heuristics."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from gitopsy.scanners.file_tree import walk_tree


# Mapping of file extension → language name
_EXTENSION_MAP: dict[str, str] = {
    ".py": "Python",
    ".pyw": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rb": "Ruby",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".less": "LESS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".mdx": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
    ".r": "R",
    ".R": "R",
    ".lua": "Lua",
    ".pl": "Perl",
    ".pm": "Perl",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hrl": "Erlang",
    ".scala": "Scala",
    ".clj": "Clojure",
    ".cljs": "Clojure",
    ".hs": "Haskell",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".tf": "Terraform",
    ".hcl": "HCL",
    ".dockerfile": "Dockerfile",
}


class LanguageStats(TypedDict):
    file_count: int
    line_count: int
    percentage: float


def detect_languages(repo_path: str) -> dict[str, LanguageStats]:
    """Detect programming languages used in a repository.

    Returns a dict mapping language name → stats dict with
    file_count, line_count, and percentage keys.
    """
    files = walk_tree(repo_path)
    if not files:
        return {}

    counts: dict[str, dict[str, int]] = {}
    total_files = 0

    for file_info in files:
        suffix = Path(file_info.path).suffix.lower()
        language = _EXTENSION_MAP.get(suffix)

        # Try the exact suffix (case-sensitive) if lowercase didn't match
        if language is None:
            language = _EXTENSION_MAP.get(Path(file_info.path).suffix)

        # Special case: Dockerfile (no extension)
        if language is None and Path(file_info.path).name == "Dockerfile":
            language = "Dockerfile"

        if language is None:
            language = "Other"

        if language not in counts:
            counts[language] = {"file_count": 0, "line_count": 0}
        counts[language]["file_count"] += 1
        counts[language]["line_count"] += file_info.line_count
        total_files += 1

    if total_files == 0:
        return {}

    result: dict[str, LanguageStats] = {}
    for lang, stats in counts.items():
        if lang == "Other":
            continue  # skip "Other" to keep output clean unless it's all we have
        result[lang] = LanguageStats(
            file_count=stats["file_count"],
            line_count=stats["line_count"],
            percentage=round(stats["file_count"] / total_files * 100, 2),
        )

    # If only "Other" was found, include it
    if not result and "Other" in counts:
        result["Other"] = LanguageStats(
            file_count=counts["Other"]["file_count"],
            line_count=counts["Other"]["line_count"],
            percentage=100.0,
        )

    # Recalculate percentages based on recognized languages only
    recognized_files = sum(v["file_count"] for v in result.values())
    if recognized_files > 0:
        for lang in result:
            result[lang]["percentage"] = round(
                result[lang]["file_count"] / recognized_files * 100, 2
            )

    return result

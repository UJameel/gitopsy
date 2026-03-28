"""Tech Debt Scorer — quantify tech debt with a single score (0-100) across 7 dimensions."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from gitopsy.models.schemas import (
    ArchitectureReport,
    DimensionScore,
    Hotspot,
    TechDebtReport,
)
from gitopsy.scanners.file_tree import walk_tree
from gitopsy.scanners.pattern_match import find_todo_comments, find_python_imports


# ---------------------------------------------------------------------------
# Dimension weights (must sum to 1.0)
# ---------------------------------------------------------------------------

_WEIGHTS: dict[str, float] = {
    "todo_density": 0.15,
    "code_staleness": 0.10,
    "test_coverage": 0.20,
    "complexity": 0.20,
    "dependency_freshness": 0.10,
    "documentation": 0.15,
    "dead_code": 0.10,
}

# Lines threshold for "complex" file
_COMPLEXITY_THRESHOLD = 500

# Docstring detection (simple regex)
_DOCSTRING_RE = re.compile(r'^\s*("""|\'\'\').*', re.MULTILINE)


def _score_todo_density(files: list, root: Path) -> DimensionScore:
    """Score TODO/FIXME/HACK density per 1000 lines."""
    total_todos = 0
    total_lines = 0

    for f in files:
        if Path(f.path).suffix not in (".py", ".js", ".ts", ".jsx", ".tsx"):
            continue
        try:
            content = (root / f.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        todos = find_todo_comments(content)
        total_todos += len(todos)
        total_lines += f.line_count

    if total_lines == 0:
        return DimensionScore(
            name="todo_density",
            score=0,
            detail="No source files found.",
            weight=_WEIGHTS["todo_density"],
        )

    density = total_todos / (total_lines / 1000)
    # 0 → 0, 5 per 1000 → 50, 10+ per 1000 → 100
    score = min(int(density * 10), 100)
    detail = f"{total_todos} TODO/FIXME/HACK comments across {total_lines} lines ({density:.1f} per 1000 lines)"

    return DimensionScore(
        name="todo_density",
        score=score,
        detail=detail,
        weight=_WEIGHTS["todo_density"],
    )


def _score_code_staleness(files: list, root: Path) -> DimensionScore:
    """Score code staleness — placeholder (no git history assumed in unit tests)."""
    # Without git history we can't compute staleness accurately.
    # Default to 0 (no penalty) with a note.
    return DimensionScore(
        name="code_staleness",
        score=0,
        detail="Code staleness analysis requires git history (not available or not computed).",
        weight=_WEIGHTS["code_staleness"],
    )


def _score_test_coverage(files: list) -> DimensionScore:
    """Score test coverage proxy: ratio of test files to source files."""
    source_files = [
        f for f in files
        if Path(f.path).suffix in (".py", ".js", ".ts", ".jsx", ".tsx")
        and "test" not in f.path.lower()
        and "spec" not in f.path.lower()
    ]
    test_files = [
        f for f in files
        if Path(f.path).suffix in (".py", ".js", ".ts", ".jsx", ".tsx")
        and (
            "test" in f.path.lower()
            or "spec" in f.path.lower()
            or Path(f.path).name.startswith("test_")
            or Path(f.path).name.endswith("_test.py")
            or Path(f.path).name.endswith(".test.js")
            or Path(f.path).name.endswith(".spec.ts")
        )
    ]

    if not source_files:
        return DimensionScore(
            name="test_coverage",
            score=0,
            detail="No source files found.",
            weight=_WEIGHTS["test_coverage"],
        )

    ratio = len(test_files) / len(source_files)
    # ratio >= 0.5 → score 0, ratio 0 → score 100
    score = max(0, min(100, int((1 - ratio * 2) * 100)))
    detail = (
        f"{len(test_files)} test files vs {len(source_files)} source files "
        f"(ratio: {ratio:.2f})"
    )

    return DimensionScore(
        name="test_coverage",
        score=score,
        detail=detail,
        weight=_WEIGHTS["test_coverage"],
    )


def _score_complexity(files: list, root: Path) -> tuple[DimensionScore, list[Hotspot]]:
    """Score complexity: based on files > 500 lines."""
    complex_files: list[tuple[str, int]] = []

    for f in files:
        if Path(f.path).suffix in (".py", ".js", ".ts", ".jsx", ".tsx"):
            if f.line_count > _COMPLEXITY_THRESHOLD:
                complex_files.append((f.path, f.line_count))

    source_files_count = sum(
        1 for f in files
        if Path(f.path).suffix in (".py", ".js", ".ts", ".jsx", ".tsx")
    )

    if source_files_count == 0:
        score = 0
    else:
        ratio = len(complex_files) / source_files_count
        score = min(100, int(ratio * 200))  # 50% complex files → score 100

    hotspots: list[Hotspot] = []
    for path, lines in sorted(complex_files, key=lambda x: x[1], reverse=True)[:10]:
        hotspots.append(
            Hotspot(
                path=path,
                reasons=[f"File has {lines} lines (threshold: {_COMPLEXITY_THRESHOLD})"],
                score=min(100, int((lines - _COMPLEXITY_THRESHOLD) / 50 + 50)),
            )
        )

    detail = (
        f"{len(complex_files)} files exceed {_COMPLEXITY_THRESHOLD} lines."
        if complex_files
        else f"No files exceed {_COMPLEXITY_THRESHOLD} lines."
    )

    return (
        DimensionScore(
            name="complexity",
            score=score,
            detail=detail,
            weight=_WEIGHTS["complexity"],
        ),
        hotspots,
    )


def _score_dependency_freshness(files: list, root: Path) -> DimensionScore:
    """Score dependency freshness — requires network to check latest versions; default low-risk."""
    return DimensionScore(
        name="dependency_freshness",
        score=0,
        detail=(
            "Dependency freshness analysis requires network access to version registries. "
            "Run with --check-deps to enable."
        ),
        weight=_WEIGHTS["dependency_freshness"],
    )


def _score_documentation(files: list, root: Path) -> DimensionScore:
    """Score documentation gaps: % of Python files without module docstrings."""
    py_files = [f for f in files if Path(f.path).suffix == ".py"]

    if not py_files:
        return DimensionScore(
            name="documentation",
            score=0,
            detail="No Python files found.",
            weight=_WEIGHTS["documentation"],
        )

    undocumented = 0
    for f in py_files:
        try:
            content = (root / f.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            undocumented += 1
            continue
        stripped = content.strip()
        # Check if file starts with a docstring
        if not (stripped.startswith('"""') or stripped.startswith("'''")):
            undocumented += 1

    ratio = undocumented / len(py_files)
    score = min(100, int(ratio * 100))
    detail = f"{undocumented}/{len(py_files)} Python files lack module docstrings ({ratio*100:.0f}%)"

    return DimensionScore(
        name="documentation",
        score=score,
        detail=detail,
        weight=_WEIGHTS["documentation"],
    )


def _score_dead_code(files: list, root: Path) -> DimensionScore:
    """Score dead code signals: files with zero imports from other files."""
    # Build a set of all imported internal modules
    referenced: set[str] = set()

    py_files = [f for f in files if Path(f.path).suffix in (".py",)]
    module_map: dict[str, str] = {Path(f.path).stem: f.path for f in py_files}

    for f in py_files:
        try:
            content = (root / f.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for imp in find_python_imports(content):
            if imp in module_map:
                referenced.add(module_map[imp])

    unreferenced = [
        f.path for f in py_files
        if f.path not in referenced
        and Path(f.path).stem != "__init__"
        and not Path(f.path).name.startswith("test_")
    ]

    if not py_files:
        return DimensionScore(
            name="dead_code",
            score=0,
            detail="No Python files found.",
            weight=_WEIGHTS["dead_code"],
        )

    ratio = len(unreferenced) / len(py_files)
    # Penalize only if more than 50% are unreferenced
    score = min(100, max(0, int((ratio - 0.5) * 200)))
    detail = (
        f"{len(unreferenced)}/{len(py_files)} Python files have no imports from internal modules."
    )

    return DimensionScore(
        name="dead_code",
        score=score,
        detail=detail,
        weight=_WEIGHTS["dead_code"],
    )


def _compute_grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score <= 20:
        return "A"
    if score <= 40:
        return "B"
    if score <= 60:
        return "C"
    if score <= 80:
        return "D"
    return "F"


def _generate_recommendations(dimensions: dict[str, DimensionScore]) -> list[str]:
    """Generate top recommendations based on worst dimensions."""
    recs: list[str] = []

    # Sort dimensions by score descending (worst first)
    worst = sorted(dimensions.values(), key=lambda d: d.score, reverse=True)

    for dim in worst[:5]:
        if dim.score == 0:
            continue
        if dim.name == "todo_density" and dim.score > 20:
            recs.append(
                f"Resolve TODO/FIXME comments ({dim.detail}) — "
                "prioritize older ones flagged by git blame."
            )
        elif dim.name == "test_coverage" and dim.score > 20:
            recs.append(
                f"Improve test coverage ({dim.detail}) — "
                "aim for a 1:1 ratio of test files to source files."
            )
        elif dim.name == "complexity" and dim.score > 20:
            recs.append(
                f"Refactor large files ({dim.detail}) — "
                f"split files over {_COMPLEXITY_THRESHOLD} lines into smaller modules."
            )
        elif dim.name == "documentation" and dim.score > 20:
            recs.append(
                f"Add module docstrings ({dim.detail}) — "
                "helps maintainability and auto-generated docs."
            )
        elif dim.name == "dead_code" and dim.score > 20:
            recs.append(
                f"Review potentially dead code ({dim.detail}) — "
                "remove or document unreferenced modules."
            )

    return recs[:5]


def analyze(
    repo_path: str,
    arch_report: ArchitectureReport | None = None,
) -> TechDebtReport:
    """Analyze tech debt in a repository.

    Args:
        repo_path: Path to the repository root.
        arch_report: Optional pre-computed ArchitectureReport to avoid re-scanning.

    Returns:
        A TechDebtReport with overall score, grade, dimensions, hotspots, and recommendations.
    """
    root = Path(repo_path).resolve()
    files = walk_tree(str(root))

    todo_dim = _score_todo_density(files, root)
    staleness_dim = _score_code_staleness(files, root)
    test_dim = _score_test_coverage(files)
    complexity_dim, hotspots = _score_complexity(files, root)
    dep_dim = _score_dependency_freshness(files, root)
    doc_dim = _score_documentation(files, root)
    dead_dim = _score_dead_code(files, root)

    dimensions = {
        "todo_density": todo_dim,
        "code_staleness": staleness_dim,
        "test_coverage": test_dim,
        "complexity": complexity_dim,
        "dependency_freshness": dep_dim,
        "documentation": doc_dim,
        "dead_code": dead_dim,
    }

    # Weighted average
    overall_score = int(
        sum(dim.score * dim.weight for dim in dimensions.values())
    )
    overall_score = max(0, min(100, overall_score))
    grade = _compute_grade(overall_score)
    recommendations = _generate_recommendations(dimensions)

    return TechDebtReport(
        overall_score=overall_score,
        grade=grade,
        dimensions=dimensions,
        hotspots=hotspots,
        recommendations=recommendations,
        trend_data=None,
    )

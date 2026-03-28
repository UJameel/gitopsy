"""Convention Detector — analyzes code style, naming, and formatting conventions."""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

from gitopsy.models.schemas import (
    ConventionReport,
    FormattingRules,
    GitConventions,
    NamingConventions,
)

_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rb", ".rs", ".cs", ".swift", ".kt",
}

_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".next"}


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


def _collect_source_files(root: Path, max_files: int = 50) -> list[Path]:
    """Return up to max_files source files, excluding test files."""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in _SOURCE_EXTENSIONS:
            continue
        # Skip test files
        name = path.name.lower()
        if "test" in name or "spec" in name or path.parent.name.lower() in ("tests", "__tests__"):
            continue
        files.append(path)
        if len(files) >= max_files:
            break
    return files


# ---------------------------------------------------------------------------
# Naming convention analysis
# ---------------------------------------------------------------------------

_SNAKE_CASE_FN = re.compile(r"\bdef\s+([a-z][a-z0-9_]*)\s*\(")
_CAMEL_CASE_FN = re.compile(r"\bfunction\s+([a-z][A-Za-z0-9]*)\s*\(")
_CAMEL_CASE_CONST = re.compile(r"\b(?:const|let|var)\s+([a-z][A-Za-z0-9]*)\s*=")
_PASCAL_CLASS = re.compile(r"\bclass\s+([A-Z][A-Za-z0-9]*)\s*[:{(]")


def _analyze_naming(files: list[Path]) -> NamingConventions:
    snake_count = 0
    camel_fn_count = 0
    camel_var_count = 0
    pascal_count = 0

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        snake_count += len(_SNAKE_CASE_FN.findall(text))
        camel_fn_count += len(_CAMEL_CASE_FN.findall(text))
        camel_var_count += len(_CAMEL_CASE_CONST.findall(text))
        pascal_count += len(_PASCAL_CLASS.findall(text))

    camel_total = camel_fn_count + camel_var_count

    functions: str | None = None
    if snake_count > 0 or camel_total > 0:
        functions = "snake_case" if snake_count >= camel_total else "camelCase"

    classes: str | None = "PascalCase" if pascal_count > 0 else None

    # Variables: infer from file types
    variables: str | None = None
    py_files = [f for f in files if f.suffix == ".py"]
    js_files = [f for f in files if f.suffix in (".js", ".ts", ".jsx", ".tsx")]
    if py_files and not js_files:
        variables = "snake_case"
    elif js_files and not py_files:
        variables = "camelCase"
    elif py_files and js_files:
        variables = "mixed"

    # File naming
    snake_files = sum(1 for f in files if "_" in f.stem and f.stem == f.stem.lower())
    kebab_files = sum(1 for f in files if "-" in f.stem)
    files_style: str | None = None
    if snake_files > kebab_files and snake_files > 0:
        files_style = "snake_case"
    elif kebab_files > snake_files and kebab_files > 0:
        files_style = "kebab-case"

    return NamingConventions(
        variables=variables,
        functions=functions,
        classes=classes,
        files=files_style,
    )


# ---------------------------------------------------------------------------
# Formatting analysis
# ---------------------------------------------------------------------------


def _analyze_formatting(files: list[Path]) -> tuple[FormattingRules, list[float]]:
    """Return (FormattingRules, list_of_consistency_violations_fraction)."""
    indent_counts: Counter[str] = Counter()
    quote_counts: Counter[str] = Counter()
    semi_count = 0
    no_semi_count = 0
    violations: list[float] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()

        # Detect indentation
        file_tabs = 0
        file_2sp = 0
        file_4sp = 0
        for line in lines:
            if line.startswith("\t"):
                file_tabs += 1
            elif line.startswith("    "):
                file_4sp += 1
            elif line.startswith("  ") and not line.startswith("   "):
                file_2sp += 1

        if file_tabs > file_4sp and file_tabs > file_2sp:
            indent_counts["tabs"] += 1
        elif file_4sp > file_2sp:
            indent_counts["4"] += 1
        elif file_2sp > 0:
            indent_counts["2"] += 1

        # Quotes (JS/TS only)
        if path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            singles = text.count("'")
            doubles = text.count('"')
            if singles > doubles:
                quote_counts["single"] += 1
            elif doubles > singles:
                quote_counts["double"] += 1

            # Semicolons: rough heuristic
            js_lines = [l for l in lines if l.strip() and not l.strip().startswith("//")]
            semi = sum(1 for l in js_lines if l.rstrip().endswith(";"))
            no_semi = sum(1 for l in js_lines if not l.rstrip().endswith(";") and l.strip())
            if semi > no_semi:
                semi_count += 1
            else:
                no_semi_count += 1

    # Majority indent style
    if not indent_counts:
        indent_style: str | None = None
        indent_width: int | None = None
    else:
        top_indent = indent_counts.most_common(1)[0][0]
        if top_indent == "tabs":
            indent_style = "tabs"
            indent_width = None
        else:
            indent_style = "spaces"
            indent_width = int(top_indent)

    # Majority quote style
    quotes: str | None = None
    if quote_counts:
        quotes = quote_counts.most_common(1)[0][0]

    # Semicolons
    semicolons: bool | None = None
    if semi_count + no_semi_count > 0:
        semicolons = semi_count >= no_semi_count

    # Consistency fraction: fraction of files deviating from majority indent
    if indent_counts and len(files) > 0:
        total_with_indent = sum(indent_counts.values())
        if total_with_indent > 0:
            majority_count = indent_counts.most_common(1)[0][1]
            deviation_frac = 1.0 - (majority_count / total_with_indent)
            violations.append(deviation_frac)

    return (
        FormattingRules(
            indent_style=indent_style,
            indent_width=indent_width,
            line_length=None,
            quotes=quotes,
            semicolons=semicolons,
        ),
        violations,
    )


# ---------------------------------------------------------------------------
# Import style analysis
# ---------------------------------------------------------------------------

_RELATIVE_IMPORT_PY = re.compile(r"from\s+\.{1,2}\S+\s+import")
_RELATIVE_IMPORT_JS = re.compile(r"""(?:import|require)\s*[\(\['"]{1}\.{1,2}/""")
_ABSOLUTE_IMPORT_PY = re.compile(r"^from\s+[a-zA-Z]", re.MULTILINE)
_ABSOLUTE_IMPORT_JS = re.compile(r"""import\s+.*from\s+['"][^.][^'"]*['"]""")


def _analyze_import_style(files: list[Path]) -> str:
    relative = 0
    absolute = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if path.suffix == ".py":
            relative += len(_RELATIVE_IMPORT_PY.findall(text))
            absolute += len(_ABSOLUTE_IMPORT_PY.findall(text))
        elif path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            relative += len(_RELATIVE_IMPORT_JS.findall(text))
            absolute += len(_ABSOLUTE_IMPORT_JS.findall(text))

    total = relative + absolute
    if total == 0:
        return "unknown"
    if relative > 0 and absolute > 0:
        ratio = relative / total
        if ratio > 0.7:
            return "relative"
        if ratio < 0.3:
            return "absolute"
        return "mixed"
    if relative > 0:
        return "relative"
    return "absolute"


# ---------------------------------------------------------------------------
# Error handling style
# ---------------------------------------------------------------------------

_TRY_EXCEPT = re.compile(r"\btry\s*:")
_TRY_CATCH = re.compile(r"\btry\s*\{")
_RESULT_TYPE = re.compile(r"\bResult<|\.unwrap\(\)|\.expect\(")
_ERROR_FIRST = re.compile(r"\(err,\s*\w+\)\s*=>|\bif\s+\(err\)\s*\{")


def _analyze_error_handling(files: list[Path]) -> str:
    try_except = 0
    try_catch = 0
    result_type = 0
    error_first = 0

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try_except += len(_TRY_EXCEPT.findall(text))
        try_catch += len(_TRY_CATCH.findall(text))
        result_type += len(_RESULT_TYPE.findall(text))
        error_first += len(_ERROR_FIRST.findall(text))

    counts = {
        "try-catch": try_except + try_catch,
        "result-type": result_type,
        "error-first": error_first,
    }
    if all(v == 0 for v in counts.values()):
        return "try-catch"
    return max(counts, key=counts.get)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test pattern detection
# ---------------------------------------------------------------------------


def _analyze_test_pattern(root: Path) -> str:
    has_tests_dir = (root / "tests").is_dir() or (root / "test").is_dir()
    has_jest_tests = bool(list(root.rglob("__tests__")))
    has_colocated = bool(list(root.rglob("*.test.js"))) or bool(list(root.rglob("*.spec.js")))

    if has_tests_dir and not has_jest_tests and not has_colocated:
        return "separate-dir"
    if has_colocated and not has_tests_dir:
        return "co-located"
    if has_jest_tests and not has_tests_dir:
        return "co-located"
    if has_tests_dir or has_jest_tests or has_colocated:
        return "mixed"
    return "unknown"


# ---------------------------------------------------------------------------
# Git conventions
# ---------------------------------------------------------------------------

_CONVENTIONAL_COMMIT = re.compile(r"^(feat|fix|chore|docs|style|refactor|test|ci|build|perf)(\(.+\))?: .+")


def _analyze_git_conventions(root: Path) -> GitConventions:
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s", "-50"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        messages = result.stdout.strip().splitlines()
    except Exception:
        messages = []

    if not messages:
        return GitConventions(commit_format=None, branch_pattern=None)

    conventional = sum(1 for m in messages if _CONVENTIONAL_COMMIT.match(m))
    if conventional / len(messages) > 0.5:
        commit_format = "conventional-commits"
    else:
        commit_format = "freeform"

    return GitConventions(commit_format=commit_format, branch_pattern=None)


# ---------------------------------------------------------------------------
# Linter config detection
# ---------------------------------------------------------------------------


def _detect_linter(root: Path) -> str | None:
    linter_files = [
        ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
        "eslint.config.js", ".pylintrc", "setup.cfg", ".flake8",
        "pyproject.toml",  # may contain [tool.ruff] or [tool.pylint]
        ".rubocop.yml", "golangci.yml",
    ]
    for name in linter_files:
        if (root / name).exists():
            return name
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze(repo_path: str) -> ConventionReport:
    """Analyze coding conventions in repo_path and return a ConventionReport."""
    root = Path(repo_path).resolve()

    files = _collect_source_files(root)

    if not files:
        return ConventionReport(
            naming=NamingConventions(variables=None, functions=None, classes=None, files=None),
            formatting=FormattingRules(
                indent_style=None, indent_width=None, line_length=None,
                quotes=None, semicolons=None,
            ),
            import_style="unknown",
            error_handling="try-catch",
            test_pattern=_analyze_test_pattern(root),
            git_conventions=_analyze_git_conventions(root),
            linter_config=_detect_linter(root),
            consistency_score=100,
        )

    naming = _analyze_naming(files)
    formatting, violations = _analyze_formatting(files)
    import_style = _analyze_import_style(files)
    error_handling = _analyze_error_handling(files)
    test_pattern = _analyze_test_pattern(root)
    git_conventions = _analyze_git_conventions(root)
    linter_config = _detect_linter(root)

    # Consistency score: 100 - avg deviation percentage
    if violations:
        avg_deviation = sum(violations) / len(violations)
        consistency_score = max(0, int(100 - avg_deviation * 100))
    else:
        consistency_score = 100

    return ConventionReport(
        naming=naming,
        formatting=formatting,
        import_style=import_style,
        error_handling=error_handling,
        test_pattern=test_pattern,
        git_conventions=git_conventions,
        linter_config=linter_config,
        consistency_score=consistency_score,
    )

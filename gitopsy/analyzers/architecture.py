"""Architecture analyzer — maps structural layout, frameworks, entry points, layers."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from gitopsy.models.schemas import (
    ArchitectureReport,
    DepEdge,
    EntryPoint,
    KeyFile,
    Layer,
)
from gitopsy.scanners.file_tree import walk_tree
from gitopsy.scanners.language_detect import detect_languages
from gitopsy.scanners.pattern_match import find_python_imports, find_javascript_imports


# ---------------------------------------------------------------------------
# Framework detection markers
# ---------------------------------------------------------------------------

_PYTHON_FRAMEWORK_MARKERS: dict[str, list[str]] = {
    "flask": ["flask"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "tornado": ["tornado"],
    "sanic": ["sanic"],
    "pyramid": ["pyramid"],
    "bottle": ["bottle"],
    "aiohttp": ["aiohttp"],
}

_JS_FRAMEWORK_MARKERS: dict[str, list[str]] = {
    "nextjs": ["next"],
    "react": ["react"],
    "express": ["express"],
    "vue": ["vue"],
    "angular": ["@angular/core"],
    "nuxt": ["nuxt"],
    "nestjs": ["@nestjs/core"],
    "svelte": ["svelte"],
    "gatsby": ["gatsby"],
    "remix": ["@remix-run/react"],
}

# Files that indicate an entry point, mapped to entry type
_ENTRY_POINT_NAMES: dict[str, str] = {
    "app.py": "web",
    "main.py": "cli",
    "server.py": "web",
    "wsgi.py": "web",
    "asgi.py": "web",
    "manage.py": "web",
    "run.py": "web",
    "cli.py": "cli",
    "__main__.py": "cli",
    "index.js": "web",
    "index.ts": "web",
    "server.js": "web",
    "server.ts": "web",
    "app.js": "web",
    "app.ts": "web",
    "main.js": "cli",
    "main.ts": "cli",
}

# Directory names that indicate architectural layers
_LAYER_DIRS: dict[str, str] = {
    "routes": "HTTP route handlers",
    "controllers": "Request controllers / handlers",
    "services": "Business logic services",
    "models": "Data models / ORM entities",
    "repositories": "Data access repositories",
    "middleware": "Middleware components",
    "utils": "Utility / helper functions",
    "helpers": "Helper functions",
    "config": "Configuration",
    "schemas": "Data schemas / serializers",
    "serializers": "Data serializers",
    "views": "View layer (MVC)",
    "templates": "HTML templates",
    "static": "Static assets",
    "api": "API layer",
    "core": "Core domain logic",
    "auth": "Authentication / authorization",
    "database": "Database layer",
    "db": "Database layer",
    "migrations": "Database migrations",
    "tasks": "Background tasks",
    "workers": "Worker processes",
    "tests": "Test suite",
    "test": "Test suite",
    "docs": "Documentation",
    "scripts": "Utility scripts",
    "lib": "Library code",
    "src": "Source code",
    "pkg": "Package code",
    "cmd": "Command-line entry points",
    "internal": "Internal packages",
    "handlers": "Request handlers",
    "store": "State store",
    "hooks": "React hooks",
    "components": "UI components",
    "pages": "Page components / Next.js pages",
}


def _detect_framework_python(requirements: str) -> str | None:
    """Detect framework from a requirements.txt or similar file."""
    for framework, markers in _PYTHON_FRAMEWORK_MARKERS.items():
        for marker in markers:
            if re.search(rf"(?i)^\s*{re.escape(marker)}[\s>=<!\[#]", requirements, re.MULTILINE):
                return framework
    return None


def _detect_framework_js(package_json: dict) -> str | None:
    """Detect framework from parsed package.json."""
    all_deps: dict[str, str] = {}
    all_deps.update(package_json.get("dependencies", {}))
    all_deps.update(package_json.get("devDependencies", {}))

    # Priority order: more specific frameworks first
    for framework, markers in _JS_FRAMEWORK_MARKERS.items():
        for marker in markers:
            if marker in all_deps:
                return framework
    return None


def _detect_framework(root: Path, files: list) -> str | None:
    """Detect the primary framework used in the repo."""
    file_names = {Path(f.path).name for f in files}
    file_map = {Path(f.path).name: f.path for f in files}

    # Check pyproject.toml / requirements.txt / setup.cfg for Python frameworks
    for req_file in ["requirements.txt", "requirements-dev.txt", "setup.cfg", "Pipfile"]:
        if req_file in file_names:
            try:
                content = (root / file_map[req_file]).read_text(
                    encoding="utf-8", errors="replace"
                )
                fw = _detect_framework_python(content)
                if fw:
                    return fw
            except OSError:
                pass

    # Check pyproject.toml
    if "pyproject.toml" in file_names:
        try:
            content = (root / file_map["pyproject.toml"]).read_text(
                encoding="utf-8", errors="replace"
            )
            fw = _detect_framework_python(content)
            if fw:
                return fw
        except OSError:
            pass

    # Check package.json for JS frameworks
    if "package.json" in file_names:
        try:
            content = (root / file_map["package.json"]).read_text(
                encoding="utf-8", errors="replace"
            )
            pkg = json.loads(content)
            fw = _detect_framework_js(pkg)
            if fw:
                return fw
        except (OSError, json.JSONDecodeError):
            pass

    # Check for Django's manage.py as a fallback
    if "manage.py" in file_names:
        return "django"

    return None


def _detect_project_type(root: Path, files: list, framework: str | None) -> str:
    """Detect project type heuristic."""
    file_names = {Path(f.path).name for f in files}
    top_dirs = {
        Path(f.path).parts[0]
        for f in files
        if len(Path(f.path).parts) > 1
    }

    # Check for monorepo signals
    if any(d in top_dirs for d in ("packages", "apps", "services", "workspaces")):
        return "monorepo"

    # CLI signals
    if framework is None or framework == "":
        if "cli.py" in file_names or "__main__.py" in file_names:
            for fname in file_names:
                if fname in ("pyproject.toml", "setup.py", "setup.cfg"):
                    try:
                        content = (root / fname).read_text(encoding="utf-8", errors="replace")
                        if "scripts" in content or "console_scripts" in content or "entry_points" in content:
                            return "cli"
                    except OSError:
                        pass
            return "cli"

    # Library signals
    if "pyproject.toml" in file_names or "setup.py" in file_names:
        # If it has a framework, it's likely not just a library
        if framework:
            return "monolith"
        for fname in file_names:
            if fname in ("pyproject.toml", "setup.py"):
                try:
                    content = (root / fname).read_text(encoding="utf-8", errors="replace")
                    if "[project]" in content and "scripts" not in content:
                        return "library"
                except OSError:
                    pass

    return "monolith"


def _detect_structure_pattern(files: list) -> str:
    """Detect structure pattern from directory names."""
    top_dirs: set[str] = set()
    for f in files:
        parts = Path(f.path).parts
        if len(parts) > 1:
            top_dirs.add(parts[0].lower())

    mvc_dirs = {"models", "views", "controllers", "routes"}
    clean_dirs = {"domain", "application", "infrastructure", "interfaces", "adapters"}
    feature_dirs_count = sum(
        1 for d in top_dirs
        if d not in mvc_dirs and d not in clean_dirs and d not in {
            "tests", "test", "docs", "scripts", "static", "templates",
            "migrations", "config", "utils", "helpers", "lib", "src",
        }
    )

    if top_dirs & clean_dirs:
        return "clean"
    if len(top_dirs & mvc_dirs) >= 2:
        return "mvc"
    if feature_dirs_count >= 2:
        return "feature-based"
    return "flat"


def _detect_entry_points(root: Path, files: list) -> list[EntryPoint]:
    """Identify entry point files."""
    entry_points: list[EntryPoint] = []
    seen: set[str] = set()

    for f in files:
        name = Path(f.path).name
        if name in _ENTRY_POINT_NAMES and f.path not in seen:
            seen.add(f.path)
            entry_points.append(
                EntryPoint(
                    path=f.path,
                    entry_type=_ENTRY_POINT_NAMES[name],
                )
            )

    return entry_points


def _detect_layers(root: Path, files: list) -> list[Layer]:
    """Identify architectural layers from directory structure."""
    dir_files: dict[str, list[str]] = defaultdict(list)

    for f in files:
        parts = Path(f.path).parts
        if len(parts) > 1:
            top_dir = parts[0].lower()
            dir_files[top_dir].append(f.path)

    layers: list[Layer] = []
    for dir_name, file_list in dir_files.items():
        if dir_name in _LAYER_DIRS:
            layers.append(
                Layer(
                    name=dir_name,
                    files=file_list,
                    purpose=_LAYER_DIRS[dir_name],
                )
            )

    return layers


def _build_dep_graph(root: Path, files: list) -> tuple[list[DepEdge], dict[str, int]]:
    """Build an internal dependency graph and return edges + in-degree counts."""
    # Map: module name → relative path
    module_map: dict[str, str] = {}
    for f in files:
        path = Path(f.path)
        # Python modules
        if path.suffix in (".py", ".pyi"):
            stem = path.stem
            module_map[stem] = f.path
            # Also map dotted path without extension
            dotted = str(path.with_suffix("")).replace("/", ".").replace("\\", ".")
            module_map[dotted] = f.path

    edges: list[DepEdge] = []
    in_degree: dict[str, int] = defaultdict(int)

    for f in files:
        abs_path = root / f.path
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if Path(f.path).suffix in (".py", ".pyi"):
            imports = find_python_imports(content)
        elif Path(f.path).suffix in (".js", ".ts", ".jsx", ".tsx", ".mjs"):
            imports = find_javascript_imports(content)
        else:
            continue

        for imp in imports:
            # Check if this import refers to an internal module
            if imp in module_map and module_map[imp] != f.path:
                target = module_map[imp]
                edges.append(DepEdge(from_module=f.path, to_module=target))
                in_degree[target] += 1

    return edges, dict(in_degree)


def _rank_key_files(files: list, in_degree: dict[str, int], entry_points: list[EntryPoint]) -> list[KeyFile]:
    """Rank files by importance using in-degree and entry point status."""
    entry_paths = {ep.path for ep in entry_points}
    key_files: list[KeyFile] = []

    # Score each file
    scored: list[tuple[int, str]] = []
    max_in = max(in_degree.values(), default=1) or 1

    for f in files:
        score = 0
        name = Path(f.path).name

        # Entry points get base score
        if f.path in entry_paths:
            score += 50

        # In-degree score (most imported = most important)
        deg = in_degree.get(f.path, 0)
        score += int(deg / max_in * 40)

        # Bonus for well-known important files
        if name in ("README.md", "pyproject.toml", "package.json", "setup.py", "Makefile"):
            score += 10

        scored.append((min(score, 100), f.path))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    for score, path in scored[:20]:
        role = "entry point" if path in entry_paths else "module"
        name = Path(path).name
        if name in ("README.md",):
            role = "documentation"
        elif name in ("pyproject.toml", "setup.py", "package.json"):
            role = "package config"

        key_files.append(KeyFile(path=path, role=role, importance_score=score))

    return key_files


def analyze(repo_path: str) -> ArchitectureReport:
    """Analyze the architecture of a repository.

    Args:
        repo_path: Path to the repository root.

    Returns:
        An ArchitectureReport with all detected architecture metadata.
    """
    root = Path(repo_path).resolve()
    files = walk_tree(str(root))
    lang_stats = detect_languages(str(root))

    # Language breakdown as percentages
    language_breakdown: dict[str, float] = {
        lang: stats["percentage"] for lang, stats in lang_stats.items()
    }

    total_files = len(files)
    total_lines = sum(f.line_count for f in files)

    framework = _detect_framework(root, files)
    project_type = _detect_project_type(root, files, framework)
    structure_pattern = _detect_structure_pattern(files)
    entry_points = _detect_entry_points(root, files)
    layers = _detect_layers(root, files)
    internal_deps, in_degree = _build_dep_graph(root, files)
    key_files = _rank_key_files(files, in_degree, entry_points)

    return ArchitectureReport(
        project_type=project_type,
        framework=framework,
        structure_pattern=structure_pattern,
        entry_points=entry_points,
        layers=layers,
        key_files=key_files,
        internal_deps=internal_deps,
        language_breakdown=language_breakdown,
        total_files=total_files,
        total_lines=total_lines,
    )

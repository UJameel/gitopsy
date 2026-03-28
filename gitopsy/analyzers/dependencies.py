"""Dependency Mapper — parses manifest files and assesses dependency health."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from gitopsy.models.schemas import Dependency, DependencyReport


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def _parse_major(version_str: str) -> int | None:
    """Return the major version integer from a version string, or None."""
    if not version_str:
        return None
    m = _SEMVER_RE.search(version_str)
    if m:
        return int(m.group(1))
    return None


def _strip_version_specifier(spec: str) -> tuple[str, str]:
    """Split 'flask==2.3.0' into ('flask', '2.3.0').

    Handles ==, >=, <=, ~=, ^, >, <, != prefixes.
    """
    # Remove extras like 'package[extra]==version'
    spec = re.sub(r"\[.*?\]", "", spec).strip()
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:[=~^<>!]+\s*(.+))?$", spec)
    if m:
        name = m.group(1).strip()
        version = (m.group(2) or "").strip()
        # strip leading =
        version = version.lstrip("=").strip()
        return name, version
    return spec.strip(), ""


# ---------------------------------------------------------------------------
# Known "old major" heuristics — major version 0 or well-known old pinned deps
# ---------------------------------------------------------------------------

_KNOWN_OUTDATED_MAJORS: dict[str, int] = {
    # package_name_lower: current_stable_major
    "flask": 3,
    "django": 5,
    "requests": 2,
    "sqlalchemy": 2,
    "fastapi": 0,  # still 0.x so not useful; skip
    "numpy": 2,
    "pandas": 2,
    "werkzeug": 3,
    "celery": 5,
}


def _determine_status(name: str, version: str) -> str:
    """Return 'ok', 'outdated', or 'unknown' for a dependency."""
    if not version:
        return "unknown"
    major = _parse_major(version)
    if major is None:
        return "unknown"
    lower = name.lower().replace("-", "_").replace(".", "_")
    # Anything pinned at major 0 for known non-0 packages is outdated
    stable_major = _KNOWN_OUTDATED_MAJORS.get(name.lower())
    if stable_major is not None and stable_major > 0 and major < stable_major - 1:
        return "outdated"
    # Generic heuristic: major 0 pinned (explicit ==0.x) is outdated for popular packages
    if major == 0 and "==" in version or (major == 0 and version.startswith("0")):
        # Older 0.x pin for packages that have moved past 1.0
        known_past_v1 = {
            "flask", "django", "requests", "werkzeug", "celery",
            "fastapi", "sqlalchemy", "aiohttp", "tornado",
        }
        if name.lower() in known_past_v1:
            return "outdated"
    return "ok"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_requirements_txt(path: Path) -> list[Dependency]:
    """Parse a requirements.txt file."""
    deps: list[Dependency] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name, version = _strip_version_specifier(line)
        if not name:
            continue
        status = _determine_status(name, version)
        deps.append(
            Dependency(
                name=name,
                current_version=version or "unknown",
                latest_version=None,
                license=None,
                status=status,
            )
        )
    return deps


def _parse_pyproject_toml(path: Path) -> list[Dependency]:
    """Parse [project.dependencies] from pyproject.toml."""
    try:
        import tomllib  # type: ignore[import]
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import]
        except ImportError:
            return []

    deps: list[Dependency] = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []

    project_deps: list[str] = data.get("project", {}).get("dependencies", [])
    for spec in project_deps:
        name, version = _strip_version_specifier(str(spec))
        if not name:
            continue
        status = _determine_status(name, version)
        deps.append(
            Dependency(
                name=name,
                current_version=version or "unknown",
                latest_version=None,
                license=None,
                status=status,
            )
        )
    return deps


def _parse_package_json(path: Path) -> tuple[list[Dependency], str | None]:
    """Parse package.json and return (deps, license_string)."""
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return [], None

    license_str: str | None = data.get("license")
    deps: list[Dependency] = []

    for section in ("dependencies", "devDependencies", "peerDependencies"):
        for name, version_spec in data.get(section, {}).items():
            version = version_spec.lstrip("^~>=<").strip()
            status = "ok" if version else "unknown"
            deps.append(
                Dependency(
                    name=name,
                    current_version=version or "unknown",
                    latest_version=None,
                    license=license_str,
                    status=status,
                )
            )
    return deps, license_str


def _parse_go_mod(path: Path) -> list[Dependency]:
    """Parse go.mod require directives."""
    deps: list[Dependency] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("require") and not re.match(r"^\S+\s+v", line):
            continue
        # 'require module/path v1.2.3'
        m = re.match(r"^(?:require\s+)?(\S+)\s+(v[\d.]+)", line)
        if m:
            name = m.group(1)
            version = m.group(2).lstrip("v")
            deps.append(
                Dependency(
                    name=name,
                    current_version=version,
                    latest_version=None,
                    license=None,
                    status="ok",
                )
            )
    return deps


def _parse_cargo_toml(path: Path) -> list[Dependency]:
    """Parse Cargo.toml [dependencies]."""
    try:
        import tomllib  # type: ignore[import]
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import]
        except ImportError:
            return []

    deps: list[Dependency] = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []

    for section in ("dependencies", "dev-dependencies"):
        for name, spec in data.get(section, {}).items():
            if isinstance(spec, str):
                version = spec.lstrip("^~>=<").strip()
            elif isinstance(spec, dict):
                version = spec.get("version", "").lstrip("^~>=<").strip()
            else:
                version = ""
            deps.append(
                Dependency(
                    name=name,
                    current_version=version or "unknown",
                    latest_version=None,
                    license=None,
                    status="ok",
                )
            )
    return deps


def _parse_gemfile(path: Path) -> list[Dependency]:
    """Parse Gemfile gem directives."""
    deps: list[Dependency] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("gem "):
            continue
        m = re.match(r"""gem\s+['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""", line)
        if m:
            name = m.group(1)
            version = (m.group(2) or "").lstrip("~>=<").strip()
            deps.append(
                Dependency(
                    name=name,
                    current_version=version or "unknown",
                    latest_version=None,
                    license=None,
                    status="ok",
                )
            )
    return deps


# ---------------------------------------------------------------------------
# Risk score
# ---------------------------------------------------------------------------


def _compute_risk_score(
    deps: list[Dependency],
    outdated_count: int,
    license_conflicts: list[str],
) -> int:
    """Compute a 0-100 risk score. Higher = riskier."""
    score = 0
    total = len(deps)
    if total == 0:
        return 0

    # Outdated fraction
    outdated_frac = outdated_count / total
    score += int(outdated_frac * 40)

    # License conflicts
    score += min(len(license_conflicts) * 15, 30)

    # Very large dependency count
    if total > 100:
        score += 20
    elif total > 50:
        score += 10

    return min(score, 100)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze(repo_path: str) -> DependencyReport:
    """Analyze dependencies in repo_path and return a DependencyReport."""
    root = Path(repo_path).resolve()

    all_deps: list[Dependency] = []
    package_manager = "unknown"
    license_str: str | None = None

    # requirements.txt
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        all_deps.extend(_parse_requirements_txt(req_txt))
        package_manager = "pip"

    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        pyproject_deps = _parse_pyproject_toml(pyproject)
        if pyproject_deps:
            all_deps.extend(pyproject_deps)
            if package_manager == "unknown":
                package_manager = "pip"

    # package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        js_deps, js_license = _parse_package_json(pkg_json)
        all_deps.extend(js_deps)
        if js_license:
            license_str = js_license
        if package_manager == "unknown" or package_manager == "pip":
            # prefer npm/yarn if js project
            if not req_txt.exists() and not pyproject.exists():
                package_manager = "npm"
            elif js_deps:
                package_manager = "npm"

    # go.mod
    go_mod = root / "go.mod"
    if go_mod.exists():
        all_deps.extend(_parse_go_mod(go_mod))
        if package_manager == "unknown":
            package_manager = "go"

    # Cargo.toml
    cargo_toml = root / "Cargo.toml"
    if cargo_toml.exists():
        all_deps.extend(_parse_cargo_toml(cargo_toml))
        if package_manager == "unknown":
            package_manager = "cargo"

    # Gemfile
    gemfile = root / "Gemfile"
    if gemfile.exists():
        all_deps.extend(_parse_gemfile(gemfile))
        if package_manager == "unknown":
            package_manager = "bundler"

    # Deduplicate by name (keep first occurrence)
    seen: set[str] = set()
    unique_deps: list[Dependency] = []
    for d in all_deps:
        key = d.name.lower()
        if key not in seen:
            seen.add(key)
            unique_deps.append(d)

    outdated_count = sum(1 for d in unique_deps if d.status == "outdated")
    license_conflicts: list[str] = []

    risk_score = _compute_risk_score(unique_deps, outdated_count, license_conflicts)

    return DependencyReport(
        package_manager=package_manager if package_manager != "unknown" else "none",
        total_deps=len(unique_deps),
        direct_deps=len(unique_deps),
        outdated_count=outdated_count,
        deps=unique_deps,
        license_conflicts=license_conflicts,
        vulnerability_count=0,
        risk_score=risk_score,
    )

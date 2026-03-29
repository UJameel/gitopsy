"""Onboarding Guide Generator — produce the guide every new hire wishes existed."""

from __future__ import annotations

import json
import re
from pathlib import Path

from gitopsy.models.schemas import (
    ArchitectureReport,
    Contributor,
    KeyFile,
    OnboardingGuide,
    SetupStep,
)
from gitopsy.scanners.file_tree import walk_tree
from gitopsy.scanners.git_history import extract_git_history


# ---------------------------------------------------------------------------
# README parsing
# ---------------------------------------------------------------------------

def _extract_readme_summary(root: Path) -> str:
    """Extract the first meaningful paragraph from README.md."""
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme = root / readme_name
        if readme.exists():
            try:
                content = readme.read_text(encoding="utf-8", errors="replace")
                return _parse_readme_summary(content)
            except OSError:
                pass
    return "No README found. Project purpose unknown."


def _parse_readme_summary(content: str) -> str:
    """Extract the first descriptive paragraph from README content."""
    lines = content.splitlines()
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            # Skip code blocks, image lines, table rows, and badge/link-only lines
            if stripped.startswith("```") or stripped.startswith("!["):
                continue
            if stripped.startswith("|"):
                continue
            # Skip badge lines like [![alt](img)](url) and pure link lines [text](url)
            if re.match(r'^\[!?\[', stripped) or re.match(r'^\[.*\]\(.*\)\s*$', stripped):
                continue
            # Strip blockquote marker, keep the text
            if stripped.startswith(">"):
                stripped = stripped[1:].strip()
                if not stripped:
                    continue
            # Strip inline markdown links [text](url) → text
            stripped = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)
            # Strip bold/italic markers
            stripped = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', stripped)
            if stripped:
                current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    # Return first non-trivial paragraph
    for p in paragraphs:
        if len(p) > 20 and not p.startswith("```"):
            return p[:500]

    return content[:200].strip() if content else "No description available."


# ---------------------------------------------------------------------------
# Setup step extraction
# ---------------------------------------------------------------------------

def _extract_setup_steps_from_readme(content: str) -> list[SetupStep]:
    """Parse installation/setup steps from README content."""
    steps: list[SetupStep] = []
    order = 1

    # Look for code blocks in installation sections
    in_install_section = False
    section_keywords = re.compile(
        r"(?i)^#+\s*(install|setup|getting started|quickstart|usage|run)",
        re.MULTILINE,
    )
    code_block_re = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)

    # Find sections
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if section_keywords.match(line):
            in_install_section = True
        elif re.match(r"^#+\s+", line) and in_install_section:
            # New section that isn't install-related — stop
            break

        if in_install_section:
            # Check for inline code blocks
            if line.strip().startswith("```"):
                code_lines: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    if lines[i].strip():
                        code_lines.append(lines[i].strip())
                    i += 1
                for cmd in code_lines:
                    steps.append(
                        SetupStep(
                            order=order,
                            description=f"Run: {cmd}",
                            command=cmd,
                        )
                    )
                    order += 1
        i += 1

    return steps


def _extract_setup_steps(root: Path, files: list) -> list[SetupStep]:
    """Extract ordered setup steps from README, package files, etc."""
    steps: list[SetupStep] = []
    file_names = {Path(f.path).name for f in files}

    # From README
    for readme_name in ("README.md", "README.rst"):
        if readme_name in file_names:
            try:
                content = (root / readme_name).read_text(encoding="utf-8", errors="replace")
                readme_steps = _extract_setup_steps_from_readme(content)
                if readme_steps:
                    return readme_steps
            except OSError:
                pass

    # Fallback: infer from package manager files
    order = 1
    if "requirements.txt" in file_names:
        steps.append(SetupStep(order=order, description="Install Python dependencies", command="pip install -r requirements.txt"))
        order += 1
    if "package.json" in file_names:
        steps.append(SetupStep(order=order, description="Install Node.js dependencies", command="npm install"))
        order += 1
    if "pyproject.toml" in file_names:
        steps.append(SetupStep(order=order, description="Install package in development mode", command="pip install -e '.[dev]'"))
        order += 1

    return steps


# ---------------------------------------------------------------------------
# Test command extraction
# ---------------------------------------------------------------------------

def _extract_test_commands(root: Path, files: list) -> list[str]:
    """Extract test commands from package.json scripts, Makefile, pytest.ini, etc."""
    commands: list[str] = []
    file_names = {Path(f.path).name for f in files}

    # package.json test script
    if "package.json" in file_names:
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8", errors="replace"))
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                commands.append(f"npm test")
            if "test:unit" in scripts:
                commands.append(f"npm run test:unit")
        except (OSError, json.JSONDecodeError):
            pass

    # pytest.ini / pyproject.toml / setup.cfg
    if "pytest.ini" in file_names or "pyproject.toml" in file_names or "setup.cfg" in file_names:
        commands.append("pytest")

    # README test section
    for readme_name in ("README.md",):
        if readme_name in file_names:
            try:
                content = (root / readme_name).read_text(encoding="utf-8", errors="replace")
                test_section = re.search(
                    r"(?i)##\s*test.*?\n(.*?)(?=\n##|\Z)",
                    content,
                    re.DOTALL,
                )
                if test_section:
                    code_blocks = re.findall(r"```[a-z]*\n(.*?)```", test_section.group(0), re.DOTALL)
                    for block in code_blocks:
                        for line in block.strip().splitlines():
                            line = line.strip()
                            if line and not line.startswith("#"):
                                if line not in commands:
                                    commands.append(line)
            except OSError:
                pass

    # Makefile test targets
    if "Makefile" in file_names:
        try:
            makefile = (root / "Makefile").read_text(encoding="utf-8", errors="replace")
            test_targets = re.findall(r"^(test[a-z-]*)\s*:", makefile, re.MULTILINE)
            for target in test_targets:
                commands.append(f"make {target}")
        except OSError:
            pass

    return list(dict.fromkeys(commands))  # deduplicate preserving order


# ---------------------------------------------------------------------------
# Gotcha detection
# ---------------------------------------------------------------------------

def _detect_gotchas(root: Path, files: list) -> list[str]:
    """Detect non-obvious things that might trip up a new developer."""
    gotchas: list[str] = []
    file_names = {Path(f.path).name for f in files}
    dirs = {Path(f.path).parts[0] for f in files if len(Path(f.path).parts) > 1}

    # Missing .env.example
    if ".env" not in file_names and ".env.example" not in file_names:
        # Check if there are environment variable references
        has_env_refs = any(
            re.search(r"os\.environ|os\.getenv|process\.env", f.path)
            for f in files
        )
        # Simple check: look for common env-using patterns
        for f in files:
            if Path(f.path).suffix in (".py", ".js", ".ts"):
                try:
                    content = (root / f.path).read_text(encoding="utf-8", errors="replace")
                    if re.search(r"os\.environ|os\.getenv|process\.env", content):
                        has_env_refs = True
                        break
                except OSError:
                    pass
        if has_env_refs:
            gotchas.append(
                "No .env.example found — developers need to discover environment variables manually."
            )

    # Missing tests directory
    has_tests = any(
        "test" in d.lower() for d in dirs
    ) or any(
        "test" in f.path.lower() or f.path.startswith("test_")
        for f in files
    )
    if not has_tests:
        gotchas.append("No tests directory found — testing status unclear.")

    # requirements.txt but no virtual env instructions
    if "requirements.txt" in file_names and "Makefile" not in file_names:
        gotchas.append(
            "No Makefile found — developers need to know manual setup steps."
        )

    # package.json with no .nvmrc or .node-version
    if "package.json" in file_names:
        if ".nvmrc" not in file_names and ".node-version" not in file_names:
            gotchas.append(
                "No .nvmrc or .node-version found — Node.js version requirements are not pinned."
            )

    return gotchas


# ---------------------------------------------------------------------------
# Glossary extraction (placeholder — deterministic version)
# ---------------------------------------------------------------------------

def _extract_glossary(files: list, root: Path) -> dict[str, str]:
    """Extract project-specific terms from code (simplified implementation)."""
    # Look for ALL_CAPS constants and class names that look project-specific
    glossary: dict[str, str] = {}
    constant_re = re.compile(r"^([A-Z][A-Z0-9_]{3,})\s*=\s*[\"']([^\"']{5,50})[\"']", re.MULTILINE)

    for f in files:
        if Path(f.path).suffix not in (".py", ".js", ".ts"):
            continue
        try:
            content = (root / f.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in constant_re.finditer(content):
            name, value = match.group(1), match.group(2)
            # Skip obvious non-glossary items
            if name in {"TODO", "FIXME", "HACK", "NOTE"} or len(name) > 30:
                continue
            glossary[name] = value
            if len(glossary) >= 10:
                break
        if len(glossary) >= 10:
            break

    return glossary


# ---------------------------------------------------------------------------
# Architecture overview
# ---------------------------------------------------------------------------

def _build_architecture_overview(arch_report: ArchitectureReport) -> str:
    """Build a human-readable architecture overview from the arch report."""
    parts: list[str] = []

    fw = f" using {arch_report.framework}" if arch_report.framework else ""
    parts.append(
        f"This is a {arch_report.project_type} project{fw} "
        f"with a {arch_report.structure_pattern} structure."
    )

    if arch_report.language_breakdown:
        top_langs = sorted(
            arch_report.language_breakdown.items(), key=lambda x: x[1], reverse=True
        )[:3]
        lang_str = ", ".join(f"{lang} ({pct:.0f}%)" for lang, pct in top_langs)
        parts.append(f"Primary languages: {lang_str}.")

    if arch_report.entry_points:
        ep_str = ", ".join(
            f"{ep.path} ({ep.entry_type})" for ep in arch_report.entry_points[:3]
        )
        parts.append(f"Entry points: {ep_str}.")

    if arch_report.layers:
        layer_str = ", ".join(layer.name for layer in arch_report.layers[:5])
        parts.append(f"Layers detected: {layer_str}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main analyze function
# ---------------------------------------------------------------------------

def analyze(repo_path: str, arch_report: ArchitectureReport) -> OnboardingGuide:
    """Generate an onboarding guide for a repository.

    Args:
        repo_path: Path to the repository root.
        arch_report: Pre-computed ArchitectureReport.

    Returns:
        An OnboardingGuide with summary, setup steps, contributors, gotchas, etc.
    """
    root = Path(repo_path).resolve()
    files = walk_tree(str(root))

    project_summary = _extract_readme_summary(root)
    architecture_overview = _build_architecture_overview(arch_report)
    key_files = arch_report.key_files[:10]
    setup_steps = _extract_setup_steps(root, files)
    test_commands = _extract_test_commands(root, files)
    gotchas = _detect_gotchas(root, files)
    glossary = _extract_glossary(files, root)

    # Contributors from git history
    git_history = extract_git_history(str(root))
    top_contributors = [
        Contributor(
            name=c.name,
            email=c.email,
            recent_commits=c.recent_commits,
        )
        for c in git_history.contributors[:10]
    ]

    return OnboardingGuide(
        project_summary=project_summary,
        architecture_overview=architecture_overview,
        key_files=key_files,
        setup_steps=setup_steps,
        test_commands=test_commands,
        top_contributors=top_contributors,
        gotchas=gotchas,
        glossary=glossary,
    )

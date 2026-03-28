"""Orchestrator — chains all analyzers and assembles the GitopsyReport."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from gitopsy.models.schemas import GitopsyReport
from gitopsy.scanners.git_history import extract_git_history


_ALL_ANALYZERS = ["arch", "debt", "onboarding", "deps", "conventions", "api", "security", "setup"]


def analyze(
    repo_path: str,
    analyzers: list[str] | None = None,
) -> GitopsyReport:
    """Run all requested analyzers on a repository and return a GitopsyReport.

    Args:
        repo_path: Absolute or relative path to the repository.
        analyzers: Optional list of analyzer names to run.
                   Defaults to all 8 analyzers.
                   Supported: "arch", "debt", "onboarding", "deps",
                              "conventions", "api", "security", "setup".

    Returns:
        A GitopsyReport containing all analyzer outputs.
    """
    root = Path(repo_path).resolve()
    run = set(analyzers) if analyzers else set(_ALL_ANALYZERS)

    project_name = root.name
    generated_at = datetime.now(timezone.utc).isoformat()

    # Try to get the current git commit hash
    git_history = extract_git_history(str(root))
    git_commit = git_history.head_commit if git_history.is_git_repo else None

    # Architecture (required for onboarding)
    arch_report = None
    if "arch" in run or "onboarding" in run:
        from gitopsy.analyzers.architecture import analyze as arch_analyze
        arch_report = arch_analyze(str(root))

    tech_debt = None
    if "debt" in run:
        from gitopsy.analyzers.tech_debt import analyze as debt_analyze
        tech_debt = debt_analyze(str(root), arch_report)

    onboarding = None
    if "onboarding" in run and arch_report is not None:
        from gitopsy.analyzers.onboarding import analyze as onbd_analyze
        onboarding = onbd_analyze(str(root), arch_report)

    dependencies = None
    if "deps" in run:
        from gitopsy.analyzers.dependencies import analyze as deps_analyze
        dependencies = deps_analyze(str(root))

    conventions = None
    if "conventions" in run:
        from gitopsy.analyzers.conventions import analyze as conv_analyze
        conventions = conv_analyze(str(root))

    api = None
    if "api" in run:
        from gitopsy.analyzers.api_extractor import analyze as api_analyze
        api = api_analyze(str(root))

    security = None
    if "security" in run:
        from gitopsy.analyzers.security_surface import analyze as sec_analyze
        security = sec_analyze(str(root))

    setup = None
    if "setup" in run:
        from gitopsy.analyzers.setup_guide import analyze as setup_analyze
        setup = setup_analyze(str(root))

    return GitopsyReport(
        repo_path=str(root),
        project_name=project_name,
        generated_at=generated_at,
        git_commit=git_commit,
        architecture=arch_report,
        tech_debt=tech_debt,
        onboarding=onboarding,
        dependencies=dependencies,
        conventions=conventions,
        api=api,
        security=security,
        setup=setup,
    )

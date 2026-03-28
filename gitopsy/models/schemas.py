"""Pydantic v2 schemas for all Gitopsy analyzer outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------


class EntryPoint(BaseModel):
    """A detected entry point file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    entry_type: str  # "web", "cli", "worker", "lib", "unknown"


class Layer(BaseModel):
    """An architectural layer (routes, services, models, etc.)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    files: list[str]
    purpose: str


class KeyFile(BaseModel):
    """An important file with its role and importance score."""

    model_config = ConfigDict(extra="forbid")

    path: str
    role: str
    importance_score: int  # 0-100


class DepEdge(BaseModel):
    """A directed edge in the internal dependency graph."""

    model_config = ConfigDict(extra="forbid")

    from_module: str
    to_module: str


class ArchitectureReport(BaseModel):
    """Full architecture analysis output."""

    model_config = ConfigDict(extra="forbid")

    project_type: str  # "monolith", "monorepo", "library", "cli"
    framework: str | None
    structure_pattern: str  # "mvc", "clean", "feature-based", "flat"
    entry_points: list[EntryPoint]
    layers: list[Layer]
    key_files: list[KeyFile]
    internal_deps: list[DepEdge]
    language_breakdown: dict[str, float]
    total_files: int
    total_lines: int


# ---------------------------------------------------------------------------
# Tech Debt
# ---------------------------------------------------------------------------


class DimensionScore(BaseModel):
    """Score for a single tech-debt dimension."""

    model_config = ConfigDict(extra="forbid")

    name: str
    score: int  # 0-100
    detail: str
    weight: float


class Hotspot(BaseModel):
    """A file flagged as a tech-debt hotspot."""

    model_config = ConfigDict(extra="forbid")

    path: str
    reasons: list[str]
    score: int  # 0-100


class TechDebtReport(BaseModel):
    """Full tech-debt analysis output."""

    model_config = ConfigDict(extra="forbid")

    overall_score: int  # 0-100
    grade: str  # A/B/C/D/F
    dimensions: dict[str, DimensionScore]
    hotspots: list[Hotspot]
    recommendations: list[str]
    trend_data: dict[str, Any] | None


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


class SetupStep(BaseModel):
    """A single setup / onboarding step."""

    model_config = ConfigDict(extra="forbid")

    order: int
    description: str
    command: str | None


class Contributor(BaseModel):
    """A project contributor derived from git history."""

    model_config = ConfigDict(extra="forbid")

    name: str
    email: str
    recent_commits: int


class OnboardingGuide(BaseModel):
    """Full onboarding guide output."""

    model_config = ConfigDict(extra="forbid")

    project_summary: str
    architecture_overview: str
    key_files: list[KeyFile]
    setup_steps: list[SetupStep]
    test_commands: list[str]
    top_contributors: list[Contributor]
    gotchas: list[str]
    glossary: dict[str, str]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


class Dependency(BaseModel):
    """A single external dependency."""

    model_config = ConfigDict(extra="forbid")

    name: str
    current_version: str
    latest_version: str | None
    license: str | None
    status: str  # "ok", "outdated", "unknown"


class DependencyReport(BaseModel):
    """Full dependency analysis output."""

    model_config = ConfigDict(extra="forbid")

    package_manager: str
    total_deps: int
    direct_deps: int
    outdated_count: int
    deps: list[Dependency]
    license_conflicts: list[str]
    vulnerability_count: int
    risk_score: int


# ---------------------------------------------------------------------------
# Conventions
# ---------------------------------------------------------------------------


class NamingConventions(BaseModel):
    """Detected naming convention patterns."""

    model_config = ConfigDict(extra="forbid")

    variables: str | None
    functions: str | None
    classes: str | None
    files: str | None


class FormattingRules(BaseModel):
    """Detected formatting rules."""

    model_config = ConfigDict(extra="forbid")

    indent_style: str | None  # "tabs" or "spaces"
    indent_width: int | None
    line_length: int | None
    quotes: str | None  # "single" or "double"
    semicolons: bool | None


class GitConventions(BaseModel):
    """Detected git conventions."""

    model_config = ConfigDict(extra="forbid")

    commit_format: str | None
    branch_pattern: str | None


class ConventionReport(BaseModel):
    """Full convention analysis output."""

    model_config = ConfigDict(extra="forbid")

    naming: NamingConventions
    formatting: FormattingRules
    import_style: str  # "relative", "absolute", "barrel", "mixed"
    error_handling: str  # "try-catch", "result-type", "error-first"
    test_pattern: str  # "co-located", "separate-dir", "mixed"
    git_conventions: GitConventions
    linter_config: str | None
    consistency_score: int  # 0-100


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


class Endpoint(BaseModel):
    """An HTTP API endpoint."""

    model_config = ConfigDict(extra="forbid")

    method: str
    path: str
    handler_file: str
    params: list[str]


class CLICommand(BaseModel):
    """A CLI command detected in the codebase."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None
    handler_file: str


class Export(BaseModel):
    """A public export from a library package."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: str  # "function", "class", "constant"
    file: str


class APIReport(BaseModel):
    """Full API surface analysis output."""

    model_config = ConfigDict(extra="forbid")

    api_type: str  # "rest", "graphql", "cli", "library", "mixed"
    endpoints: list[Endpoint]
    graphql_types: list[str] | None
    cli_commands: list[CLICommand] | None
    public_exports: list[Export]
    total_routes: int
    undocumented_routes: int


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class SecurityFinding(BaseModel):
    """A single security finding."""

    model_config = ConfigDict(extra="forbid")

    severity: str  # "low", "medium", "high", "critical"
    category: str
    file: str
    line: int | None
    description: str


class SecurityReport(BaseModel):
    """Full security surface analysis output."""

    model_config = ConfigDict(extra="forbid")

    risk_level: str  # "low", "medium", "high", "critical"
    findings: list[SecurityFinding]
    secrets_found: int
    env_files_in_git: list[str]
    exposed_ports: list[int]
    auth_pattern: str | None
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Setup Guide
# ---------------------------------------------------------------------------


class Prerequisite(BaseModel):
    """A prerequisite tool or runtime."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str | None
    install_url: str | None


class EnvVar(BaseModel):
    """An environment variable."""

    model_config = ConfigDict(extra="forbid")

    name: str
    required: bool
    description: str | None
    example: str | None


class Issue(BaseModel):
    """A common issue and its solution."""

    model_config = ConfigDict(extra="forbid")

    description: str
    solution: str


class SetupGuide(BaseModel):
    """Full setup guide output."""

    model_config = ConfigDict(extra="forbid")

    prerequisites: list[Prerequisite]
    install_steps: list[SetupStep]
    env_vars: list[EnvVar]
    database_setup: list[SetupStep] | None
    build_command: str | None
    run_commands: dict[str, str]
    test_command: str | None
    common_issues: list[Issue]


# ---------------------------------------------------------------------------
# Top-level Report
# ---------------------------------------------------------------------------


class GitopsyReport(BaseModel):
    """The full Gitopsy report wrapping all analyzer outputs."""

    model_config = ConfigDict(extra="forbid")

    repo_path: str
    project_name: str
    generated_at: str
    git_commit: str | None

    architecture: ArchitectureReport | None = None
    tech_debt: TechDebtReport | None = None
    onboarding: OnboardingGuide | None = None
    dependencies: DependencyReport | None = None
    conventions: ConventionReport | None = None
    api: APIReport | None = None
    security: SecurityReport | None = None
    setup: SetupGuide | None = None

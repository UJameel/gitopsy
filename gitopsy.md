# Gitopsy — Project Architecture

> *Dissect any codebase in seconds.*

## What Is Gitopsy?

Gitopsy is an open-source codebase intelligence engine that deeply analyzes any repository and produces a beautiful, interactive HTML report covering architecture, onboarding, tech debt, dependencies, conventions, APIs, security surface, and setup — everything a developer needs to understand an unfamiliar codebase.

It works as both a **Claude Code skill system** (`/gitopsy`) and a **standalone Python CLI** (`gitopsy .`).

---

## Repository Structure

```
gitopsy/
├── README.md
├── LICENSE                          # MIT
├── pyproject.toml                   # Python package config (pip install gitopsy)
├── setup.cfg
│
├── .claude/
│   └── skills/
│       └── gitopsy/
│           └── SKILL.md             # Master orchestrator skill
│
├── gitopsy/                         # Python package
│   ├── __init__.py
│   ├── __main__.py                  # CLI entry: `python -m gitopsy` or `gitopsy .`
│   ├── cli.py                       # Click-based CLI interface
│   ├── orchestrator.py              # Chains all analyzers, assembles final report
│   │
│   ├── analyzers/                   # Each analyzer = one "skill"
│   │   ├── __init__.py
│   │   ├── architecture.py          # Architecture Analyzer
│   │   ├── onboarding.py            # Onboarding Guide Generator
│   │   ├── tech_debt.py             # Tech Debt Scorer
│   │   ├── dependencies.py          # Dependency Mapper
│   │   ├── conventions.py           # Convention Detector
│   │   ├── api_extractor.py         # API Extractor
│   │   ├── security_surface.py      # Security Surface Scanner
│   │   └── setup_guide.py           # Setup Guide Builder
│   │
│   ├── report/                      # HTML report generation
│   │   ├── __init__.py
│   │   ├── renderer.py              # Jinja2 → HTML assembler
│   │   ├── template.html            # Single-file HTML template (inline CSS/JS)
│   │   └── charts.py                # Chart data generators (Chart.js payloads)
│   │
│   ├── scanners/                    # Low-level file system utilities
│   │   ├── __init__.py
│   │   ├── file_tree.py             # Directory walker with .gitignore respect
│   │   ├── git_history.py           # Git log/blame/stats extraction
│   │   ├── language_detect.py       # Language detection (extensions + heuristics)
│   │   └── pattern_match.py         # Regex/AST pattern matching utilities
│   │
│   └── models/                      # Pydantic data models for all analyzer outputs
│       ├── __init__.py
│       └── schemas.py               # Typed schemas: ArchitectureReport, DebtScore, etc.
│
├── tests/
│   ├── test_architecture.py
│   ├── test_onboarding.py
│   ├── test_tech_debt.py
│   ├── test_dependencies.py
│   ├── test_conventions.py
│   ├── test_api_extractor.py
│   ├── test_security.py
│   ├── test_setup_guide.py
│   └── fixtures/                    # Sample repos for testing
│       ├── flask-app/
│       ├── nextjs-app/
│       └── python-cli/
│
└── docs/
    ├── CONTRIBUTING.md
    └── examples/                    # Example reports for the README
        ├── gitopsy-report-flask.html
        └── screenshots/
            ├── overview.png
            ├── architecture-tab.png
            └── tech-debt-tab.png
```

---

## Dual-Mode Design

### Mode 1: Claude Code Skill (`/gitopsy`)

The SKILL.md orchestrator tells Claude to:
1. Run the Python analyzers via bash
2. Collect all JSON outputs
3. Render the HTML report
4. Present it to the user

This gives Claude Code users the full experience with zero setup beyond having Python available.

### Mode 2: Standalone CLI (`gitopsy .`)

```bash
pip install gitopsy
gitopsy .                          # Analyze current directory
gitopsy /path/to/repo              # Analyze any repo
gitopsy . --output report.html     # Custom output path
gitopsy . --analyzers arch,debt    # Run specific analyzers only
gitopsy . --json                   # Output raw JSON (for piping)
```

Same analyzers, same output. The CLI calls orchestrator.py directly.

---

## Analyzer Specifications

### 1. Architecture Analyzer (`architecture.py`)

**Purpose:** Map the structural layout, identify patterns, entry points, and layers.

**What it detects:**
- Project type (monorepo, microservice, monolith, library, CLI tool)
- Framework detection (Next.js, Flask, Django, Express, FastAPI, Rails, etc.)
- Directory structure pattern (MVC, Clean Architecture, feature-based, flat)
- Entry points (main files, index files, app bootstrappers)
- Layer identification (routes, controllers, services, models, utils, config)
- Module dependency graph (which internal modules import which)
- File importance ranking (by import count, centrality)

**Output schema:**
```python
class ArchitectureReport:
    project_type: str               # "monolith", "monorepo", "library", "cli"
    framework: str | None           # "nextjs", "flask", "express", etc.
    structure_pattern: str          # "mvc", "clean", "feature-based", "flat"
    entry_points: list[EntryPoint]  # file path + type (web, cli, worker, etc.)
    layers: list[Layer]             # name, files, purpose
    key_files: list[KeyFile]        # path, role, importance_score (0-100)
    internal_deps: list[DepEdge]    # from_module → to_module
    language_breakdown: dict        # {"Python": 65.2, "JavaScript": 30.1, ...}
    total_files: int
    total_lines: int
```

**How it works (no AI needed — deterministic):**
1. Walk file tree, classify by extension
2. Parse known framework markers (package.json scripts, manage.py, etc.)
3. Detect structure via directory naming heuristics
4. Parse imports (regex-based, not full AST) to build dep graph
5. Rank files by in-degree (most imported = most important)

---

### 2. Onboarding Guide Generator (`onboarding.py`)

**Purpose:** Generate the doc that every new hire wishes existed.

**What it produces:**
- "What is this project?" — one-paragraph summary derived from README + package metadata
- "How is it organized?" — simplified architecture overview (from analyzer #1)
- "Key files to read first" — ranked list with explanations
- "How to run it locally" — extracted from README, Makefile, docker-compose, scripts
- "How to run tests" — detected from package.json scripts, pytest.ini, Makefile
- "Who to ask" — top contributors by git blame (recent activity weighted)
- "Gotchas" — unusual patterns, non-obvious config, known quirks

**Output schema:**
```python
class OnboardingGuide:
    project_summary: str
    architecture_overview: str       # Simplified from ArchitectureReport
    key_files: list[KeyFile]         # Top 10 files to read, with why
    setup_steps: list[SetupStep]     # Ordered steps to get running
    test_commands: list[str]
    top_contributors: list[Contributor]  # name, email, recent_commits
    gotchas: list[str]               # Non-obvious things
    glossary: dict[str, str]         # Project-specific terms found in code
```

---

### 3. Tech Debt Scorer (`tech_debt.py`)

**Purpose:** Quantify tech debt with a single score (0-100) broken into dimensions.

**Dimensions scored:**
- **TODO/FIXME/HACK density** — count per 1000 lines, weighted by age
- **Code staleness** — % of files not touched in 6+ months
- **Test coverage proxy** — ratio of test files to source files
- **Complexity hotspots** — files with extreme line counts (>500 lines)
- **Dependency freshness** — % of deps more than 1 major version behind
- **Documentation gaps** — % of public modules/functions without docstrings
- **Dead code signals** — files with zero imports from other files

**Output schema:**
```python
class TechDebtReport:
    overall_score: int               # 0 (pristine) to 100 (on fire)
    grade: str                       # A/B/C/D/F
    dimensions: dict[str, DimensionScore]  # Each dimension with score + detail
    hotspots: list[Hotspot]          # Worst files with specific reasons
    recommendations: list[str]       # Top 5 actionable fixes
    trend_data: dict | None          # If git history available, debt over time
```

---

### 4. Dependency Mapper (`dependencies.py`)

**Purpose:** Full picture of external dependencies — what, how old, how risky.

**What it detects:**
- All declared dependencies (package.json, requirements.txt, pyproject.toml, Gemfile, go.mod, Cargo.toml, etc.)
- Direct vs transitive (where possible)
- Current version vs latest available
- License of each dependency
- License compatibility warnings (e.g., GPL in MIT project)
- Known vulnerability flags (via OSV/advisory databases — optional, requires network)
- Dependency age (time since last publish)
- "Bus factor" deps — dependencies with 1 maintainer

**Output schema:**
```python
class DependencyReport:
    package_manager: str             # "npm", "pip", "cargo", etc.
    total_deps: int
    direct_deps: int
    outdated_count: int
    deps: list[Dependency]           # name, current, latest, license, age, status
    license_conflicts: list[str]
    vulnerability_count: int
    risk_score: int                  # 0-100
```

---

### 5. Convention Detector (`conventions.py`)

**Purpose:** Reverse-engineer the unwritten rules of the codebase.

**What it detects:**
- Naming conventions (camelCase vs snake_case vs PascalCase — per language)
- File naming patterns (kebab-case.ts vs PascalCase.tsx)
- Import style (relative vs absolute, barrel files, path aliases)
- Formatting signals (tabs vs spaces, indent width, line length)
- Error handling patterns (try/catch style, Result types, error-first callbacks)
- State management patterns (Redux, Zustand, Context, Pinia, etc.)
- Testing patterns (test co-location vs separate directory, naming)
- Git conventions (commit message format, branch naming)

**Output schema:**
```python
class ConventionReport:
    naming: NamingConventions        # variable, function, class, file patterns
    formatting: FormattingRules      # indent, line_length, quotes, semicolons
    import_style: str                # "relative", "absolute", "barrel", "mixed"
    error_handling: str              # "try-catch", "result-type", "error-first"
    test_pattern: str                # "co-located", "separate-dir", "mixed"
    git_conventions: GitConventions  # commit format, branch pattern
    linter_config: str | None        # Detected linter + key rules
    consistency_score: int           # 0-100 (how consistently conventions are followed)
```

---

### 6. API Extractor (`api_extractor.py`)

**Purpose:** Find and document all API endpoints, routes, and public interfaces.

**What it detects:**
- HTTP routes (Express, Flask, FastAPI, Django, Rails, Next.js API routes)
- Route parameters and methods (GET/POST/PUT/DELETE)
- GraphQL schemas (if present)
- CLI commands (Click, argparse, Commander.js)
- Exported functions/classes in library packages
- WebSocket endpoints
- Event handlers / message queue consumers

**Output schema:**
```python
class APIReport:
    api_type: str                    # "rest", "graphql", "cli", "library", "mixed"
    endpoints: list[Endpoint]        # method, path, handler_file, params
    graphql_types: list[str] | None
    cli_commands: list[CLICommand] | None
    public_exports: list[Export]     # For libraries: exported functions/classes
    total_routes: int
    undocumented_routes: int
```

---

### 7. Security Surface Scanner (`security_surface.py`)

**Purpose:** Map the attack surface — not a full audit, but a fast risk overview.

**What it detects:**
- Hardcoded secrets/API keys (regex patterns for common key formats)
- .env files committed to git
- Exposed ports in Docker/docker-compose
- CORS configuration
- Authentication patterns (JWT, session, OAuth — detected, not audited)
- SQL query construction (raw string interpolation = flag)
- Dependency vulnerabilities (from dep mapper)
- Missing security headers (if config files detected)
- File permission issues (.env readable, secrets not in .gitignore)

**Output schema:**
```python
class SecurityReport:
    risk_level: str                  # "low", "medium", "high", "critical"
    findings: list[SecurityFinding]  # severity, category, file, line, description
    secrets_found: int
    env_files_in_git: list[str]
    exposed_ports: list[int]
    auth_pattern: str | None
    recommendations: list[str]
```

---

### 8. Setup Guide Builder (`setup_guide.py`)

**Purpose:** Auto-generate the "how to get this running from zero" guide.

**What it detects and produces:**
- Prerequisites (Node version, Python version, Docker, database, etc.)
- Install commands (from package.json, requirements.txt, Makefile, etc.)
- Environment variable template (from .env.example, code scanning for os.environ/process.env)
- Database setup steps (from docker-compose, migration files, seed scripts)
- Build commands
- Run commands (dev server, production, workers)
- Test commands
- Common errors and solutions (from README, TROUBLESHOOTING.md if exists)

**Output schema:**
```python
class SetupGuide:
    prerequisites: list[Prerequisite]  # name, version, install_url
    install_steps: list[Step]
    env_vars: list[EnvVar]            # name, required, description, example
    database_setup: list[Step] | None
    build_command: str | None
    run_commands: dict[str, str]      # {"dev": "npm run dev", "prod": "npm start"}
    test_command: str | None
    common_issues: list[Issue]
```

---

## HTML Report Design

Single self-contained HTML file (inline CSS + JS, no external deps). Opens in any browser.

### Layout:
- **Header**: Project name, Gitopsy branding, generation timestamp, git commit hash
- **Score Dashboard**: Overall health score (A-F), with mini scores for each dimension
- **Tabbed Navigation**: One tab per analyzer
  - Architecture (interactive file tree + dep graph)
  - Onboarding (the readable guide)
  - Tech Debt (scores + hotspot table + chart)
  - Dependencies (table with status badges + license column)
  - Conventions (detected rules, consistency score)
  - APIs (endpoint table, method badges)
  - Security (findings list, severity badges)
  - Setup (step-by-step guide, copy-paste commands)

### Design Direction:
- Dark theme by default (developer audience)
- Monospace headings, clean sans-serif body
- Color-coded severity/scores (green/yellow/orange/red)
- Collapsible sections for detail
- Search/filter on tables
- Chart.js for debt scores and language breakdown
- Zero external dependencies — everything inline

---

## Release Phases

### Phase 1: MVP (ship in 1 week)
- Architecture Analyzer
- Tech Debt Scorer
- Onboarding Guide Generator
- HTML report with 3 tabs
- CLI working (`gitopsy .`)
- SKILL.md orchestrator working (`/gitopsy`)
- README with screenshots
- PyPI package published

### Phase 2: Full Suite (week 2-3)
- Dependency Mapper
- Convention Detector
- Security Surface Scanner
- Setup Guide Builder
- API Extractor
- Full 8-tab HTML report
- Score dashboard

### Phase 3: Polish & Virality (week 3-4)
- GitHub Action (run gitopsy on any repo in CI)
- Badge generation ("Gitopsy Score: A")
- Comparison mode (diff two reports over time)
- Example reports for famous repos (React, Flask, FastAPI)
- Demo GIF for README
- Hacker News / Reddit launch

---

## Technical Constraints

1. **Python only** — no Node.js, no Go
2. **Zero mandatory external API calls** — everything works offline
3. **Minimal dependencies** — Jinja2 for HTML, Click for CLI, Pydantic for schemas. That's it.
4. **Fast** — must analyze a 10k-file repo in under 30 seconds
5. **Git-optional** — works on any directory, git history enables bonus features
6. **No AI required for CLI mode** — all analysis is deterministic (regex, heuristics, file parsing)
7. **AI-enhanced in skill mode** — Claude can add summaries, explanations, and recommendations

---

## Competitive Moat

| Existing Tool | What It Does | Why Gitopsy Wins |
|---|---|---|
| `gitingest` | Dumps repo to text for LLM context | No analysis, just raw dump |
| `repomap` (Aider) | AST-based file importance ranking | Single dimension, no report |
| CodeClimate | Cloud-based code quality | Paid, requires account, no onboarding |
| `deeprepo` | RAG-based codebase Q&A | Requires LLM API, not a report |
| SonarQube | Static analysis | Enterprise, heavy, no onboarding/setup |
| Gitopsy | **Full codebase intelligence report** | Free, local, one command, beautiful HTML |

---

## Name Assets to Secure

- [x] GitHub: `gitopsy` (create immediately)
- [ ] PyPI: `gitopsy`
- [ ] npm: `gitopsy` (reserve even if Python-first)
- [ ] Domain: `gitopsy.dev` or `gitopsy.io`
- [ ] Twitter/X: `@gitopsy`
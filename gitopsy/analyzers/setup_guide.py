"""Setup Guide Builder — generates actionable setup documentation from repo structure."""

from __future__ import annotations

import re
from pathlib import Path

from gitopsy.models.schemas import EnvVar, Issue, Prerequisite, SetupGuide, SetupStep

_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".next"}

# ---------------------------------------------------------------------------
# Prerequisite detection
# ---------------------------------------------------------------------------


def _detect_prerequisites(root: Path) -> list[Prerequisite]:
    """Detect required tools and runtimes."""
    prereqs: list[Prerequisite] = []

    # Python
    has_python = (
        (root / "requirements.txt").exists()
        or (root / "setup.py").exists()
        or (root / "setup.cfg").exists()
        or (root / "pyproject.toml").exists()
    )
    if has_python:
        python_version: str | None = None

        # Try pyproject.toml for python_requires
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="replace")
                m = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    python_version = m.group(1)
            except OSError:
                pass

        # Try setup.cfg
        setup_cfg = root / "setup.cfg"
        if setup_cfg.exists() and not python_version:
            try:
                content = setup_cfg.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"python_requires\s*=\s*(.+)", content)
                if m:
                    python_version = m.group(1).strip()
            except OSError:
                pass

        prereqs.append(
            Prerequisite(
                name="python",
                version=python_version,
                install_url="https://python.org/downloads",
            )
        )

    # Node.js
    pkg_json = root / "package.json"
    if pkg_json.exists():
        node_version: str | None = None
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            engines = data.get("engines", {})
            node_version = engines.get("node")
        except Exception:
            pass

        prereqs.append(
            Prerequisite(
                name="node.js",
                version=node_version,
                install_url="https://nodejs.org",
            )
        )

    # Docker
    has_docker = (
        (root / "docker-compose.yml").exists()
        or (root / "docker-compose.yaml").exists()
        or (root / "Dockerfile").exists()
    )
    if has_docker:
        prereqs.append(
            Prerequisite(
                name="docker",
                version=None,
                install_url="https://docs.docker.com/get-docker/",
            )
        )

    # Go
    if (root / "go.mod").exists():
        go_version: str | None = None
        try:
            content = (root / "go.mod").read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^go\s+(\d+\.\d+)", content, re.MULTILINE)
            if m:
                go_version = m.group(1)
        except OSError:
            pass
        prereqs.append(
            Prerequisite(
                name="go",
                version=go_version,
                install_url="https://go.dev/doc/install",
            )
        )

    # Rust
    if (root / "Cargo.toml").exists():
        prereqs.append(
            Prerequisite(
                name="rust",
                version=None,
                install_url="https://rustup.rs",
            )
        )

    return prereqs


# ---------------------------------------------------------------------------
# Install steps
# ---------------------------------------------------------------------------


def _build_install_steps(root: Path) -> list[SetupStep]:
    """Generate install steps based on detected package managers."""
    steps: list[SetupStep] = []
    order = 1

    # Git clone (generic first step)
    # Skip — user already has repo

    # Python: requirements.txt
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        steps.append(
            SetupStep(
                order=order,
                description="Install Python dependencies",
                command="pip install -r requirements.txt",
            )
        )
        order += 1

    # Python: pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists() and not req_txt.exists():
        steps.append(
            SetupStep(
                order=order,
                description="Install the package in development mode",
                command="pip install -e .",
            )
        )
        order += 1
    elif pyproject.exists() and req_txt.exists():
        # Both — add editable install too if it's a proper package
        try:
            import tomllib  # type: ignore[import]
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[import]
            except ImportError:
                tomllib = None  # type: ignore[assignment]
        if tomllib is not None:
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8", errors="replace"))
                if data.get("project", {}).get("name"):
                    steps.append(
                        SetupStep(
                            order=order,
                            description="Install the package in development mode",
                            command="pip install -e .",
                        )
                    )
                    order += 1
            except Exception:
                pass

    # Node.js
    pkg_json = root / "package.json"
    if pkg_json.exists():
        # Check for yarn.lock or package-lock.json
        if (root / "yarn.lock").exists():
            cmd = "yarn install"
        elif (root / "pnpm-lock.yaml").exists():
            cmd = "pnpm install"
        else:
            cmd = "npm install"
        steps.append(
            SetupStep(
                order=order,
                description="Install Node.js dependencies",
                command=cmd,
            )
        )
        order += 1

    # Copy .env.example if it exists
    if (root / ".env.example").exists():
        steps.append(
            SetupStep(
                order=order,
                description="Set up environment variables",
                command="cp .env.example .env",
            )
        )
        order += 1

    # Go
    if (root / "go.mod").exists():
        steps.append(
            SetupStep(
                order=order,
                description="Download Go dependencies",
                command="go mod download",
            )
        )
        order += 1

    # Rust
    if (root / "Cargo.toml").exists():
        steps.append(
            SetupStep(
                order=order,
                description="Build the project",
                command="cargo build",
            )
        )
        order += 1

    return steps


# ---------------------------------------------------------------------------
# Environment variable extraction
# ---------------------------------------------------------------------------

_PYTHON_ENV_RE = re.compile(r"""os\.environ\.get\(\s*['"]([A-Z_][A-Z0-9_]*)['"]""")
_PROCESS_ENV_RE = re.compile(r"""process\.env\.([A-Z_][A-Z0-9_]*)""")
_ENV_LINE_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$")


def _extract_env_vars(root: Path) -> list[EnvVar]:
    """Extract environment variables from .env.example and source files."""
    env_vars: dict[str, EnvVar] = {}

    # Parse .env.example
    env_example = root / ".env.example"
    if env_example.exists():
        try:
            for line in env_example.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = _ENV_LINE_RE.match(line)
                if m:
                    name = m.group(1)
                    example = m.group(2).strip()
                    env_vars[name] = EnvVar(
                        name=name,
                        required=True,
                        description=None,
                        example=example or None,
                    )
        except OSError:
            pass

    # Parse .env (if exists, for discovery only)
    env_file = root / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = _ENV_LINE_RE.match(line)
                if m:
                    name = m.group(1)
                    if name not in env_vars:
                        env_vars[name] = EnvVar(
                            name=name,
                            required=False,
                            description=None,
                            example=None,
                        )
        except OSError:
            pass

    # Scan Python source files
    for path in sorted(root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _PYTHON_ENV_RE.finditer(content):
            name = m.group(1)
            if name not in env_vars:
                env_vars[name] = EnvVar(
                    name=name,
                    required=False,
                    description=None,
                    example=None,
                )

    # Scan JS/TS source files
    for path in sorted(root.rglob("*.js")) or sorted(root.rglob("*.ts")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _PROCESS_ENV_RE.finditer(content):
            name = m.group(1)
            if name not in env_vars:
                env_vars[name] = EnvVar(
                    name=name,
                    required=False,
                    description=None,
                    example=None,
                )

    return list(env_vars.values())


# ---------------------------------------------------------------------------
# Database detection
# ---------------------------------------------------------------------------


def _detect_database_setup(root: Path) -> list[SetupStep] | None:
    """Detect database setup from docker-compose.yml."""
    compose_files = ["docker-compose.yml", "docker-compose.yaml"]
    for fname in compose_files:
        compose_path = root / fname
        if not compose_path.exists():
            continue
        try:
            content = compose_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(svc in content for svc in ("postgres", "mysql", "mongodb", "redis")):
            return [
                SetupStep(
                    order=1,
                    description="Start the database services",
                    command="docker-compose up -d db",
                )
            ]
    return None


# ---------------------------------------------------------------------------
# Run command extraction from README
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(?:bash|sh|shell|console)?\n(.*?)```", re.DOTALL)
_RUN_KEYWORDS = ["flask run", "uvicorn", "gunicorn", "npm run", "yarn dev", "python ", "node "]


def _extract_run_commands(root: Path) -> dict[str, str]:
    """Extract run commands from README files."""
    run_commands: dict[str, str] = {}

    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme = root / readme_name
        if not readme.exists():
            continue
        try:
            content = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for m in _CODE_BLOCK_RE.finditer(content):
            block = m.group(1).strip()
            for line in block.splitlines():
                line = line.strip()
                for keyword in _RUN_KEYWORDS:
                    if keyword in line.lower():
                        label = keyword.split()[0]
                        if label not in run_commands:
                            run_commands[label] = line
                        break

    # Also check package.json scripts
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            scripts = data.get("scripts", {})
            if "dev" in scripts:
                run_commands["dev"] = "npm run dev"
            if "start" in scripts:
                run_commands["start"] = "npm start"
        except Exception:
            pass

    return run_commands


# ---------------------------------------------------------------------------
# Test command detection
# ---------------------------------------------------------------------------


def _detect_test_command(root: Path) -> str | None:
    """Detect the primary test command."""
    # pytest
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        try:
            content = req_txt.read_text(encoding="utf-8", errors="replace")
            if "pytest" in content.lower():
                return "pytest"
        except OSError:
            pass

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="replace")
            if "pytest" in content.lower() or "[tool.pytest" in content:
                return "pytest"
        except OSError:
            pass

    # Jest / npm test
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            scripts = data.get("scripts", {})
            if "test" in scripts:
                if "jest" in scripts["test"].lower():
                    return "jest"
                return scripts["test"]
        except Exception:
            pass

    # Go test
    if (root / "go.mod").exists():
        return "go test ./..."

    # Cargo test
    if (root / "Cargo.toml").exists():
        return "cargo test"

    return None


# ---------------------------------------------------------------------------
# Common issues
# ---------------------------------------------------------------------------


def _generate_common_issues(root: Path, prereqs: list[Prerequisite]) -> list[Issue]:
    issues: list[Issue] = []
    prereq_names = {p.name.lower() for p in prereqs}

    if "python" in prereq_names:
        issues.append(
            Issue(
                description="ModuleNotFoundError when running the app",
                solution="Make sure you've activated your virtual environment and run `pip install -r requirements.txt`",
            )
        )

    if "node.js" in prereq_names or "node" in prereq_names:
        issues.append(
            Issue(
                description="Cannot find module errors in Node.js",
                solution="Run `npm install` to install all dependencies",
            )
        )

    if (root / ".env.example").exists():
        issues.append(
            Issue(
                description="Missing environment variables causing runtime errors",
                solution="Copy .env.example to .env and fill in the required values",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze(repo_path: str) -> SetupGuide:
    """Analyze repo_path and return a SetupGuide."""
    root = Path(repo_path).resolve()

    prerequisites = _detect_prerequisites(root)
    install_steps = _build_install_steps(root)
    env_vars = _extract_env_vars(root)
    database_setup = _detect_database_setup(root)
    run_commands = _extract_run_commands(root)
    test_command = _detect_test_command(root)
    common_issues = _generate_common_issues(root, prerequisites)

    # Build command (if applicable)
    build_command: str | None = None
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            if "build" in data.get("scripts", {}):
                build_command = "npm run build"
        except Exception:
            pass

    return SetupGuide(
        prerequisites=prerequisites,
        install_steps=install_steps,
        env_vars=env_vars,
        database_setup=database_setup,
        build_command=build_command,
        run_commands=run_commands,
        test_command=test_command,
        common_issues=common_issues,
    )

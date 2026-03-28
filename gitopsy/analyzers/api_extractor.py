"""API Extractor — detects HTTP routes, CLI commands, and public exports."""

from __future__ import annotations

import re
from pathlib import Path

from gitopsy.models.schemas import APIReport, CLICommand, Endpoint, Export

_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".next"}

# ---------------------------------------------------------------------------
# Flask / Werkzeug route patterns
# ---------------------------------------------------------------------------

# Matches: @app.route("/path", methods=["GET", "POST"])
#          @blueprint.route("/path")
_FLASK_ROUTE_RE = re.compile(
    r'@\w+\.route\(\s*["\']([^"\']+)["\']\s*(?:,\s*methods\s*=\s*\[([^\]]*)\])?\s*\)',
)

# Matches docstrings immediately after def
_DOCSTRING_RE = re.compile(r'def\s+\w+[^:]*:\s*(?:\n\s*"""|\n\s*\'\'\')')


# ---------------------------------------------------------------------------
# FastAPI patterns
# ---------------------------------------------------------------------------

_FASTAPI_ROUTE_RE = re.compile(
    r'@(?:\w+)\.(?:(get|post|put|delete|patch|options|head))\(\s*["\']([^"\']+)["\']\s*\)',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Express.js patterns
# ---------------------------------------------------------------------------

_EXPRESS_ROUTE_RE = re.compile(
    r'(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']\s*,',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Django URL patterns
# ---------------------------------------------------------------------------

_DJANGO_URL_RE = re.compile(
    r"""path\(\s*['"]([\w/<>:]+)['"]\s*,""",
)

_DJANGO_RE_PATH_RE = re.compile(
    r"""re_path\(\s*r?['"]([^'"]+)['"]\s*,""",
)


# ---------------------------------------------------------------------------
# Click / argparse CLI patterns
# ---------------------------------------------------------------------------

_CLICK_COMMAND_RE = re.compile(
    r'@(?:\w+)\.command\(\s*(?:["\']([^"\']*)["\'])?\s*\)'
)
_CLICK_GROUP_CMD_RE = re.compile(
    r'def\s+([a-z_][a-z0-9_]*)\s*\([^)]*\)\s*(?:->\s*\w+\s*)?:\s*\n\s*(?:"""([^"]*?)""")?',
    re.DOTALL,
)
_ARGPARSE_ADD_PARSER = re.compile(
    r'add_parser\(\s*["\']([^"\']+)["\']\s*(?:,\s*help\s*=\s*["\']([^"\']+)["\']\s*)?\)',
)


# ---------------------------------------------------------------------------
# Next.js API routes
# ---------------------------------------------------------------------------


def _extract_nextjs_routes(root: Path) -> list[Endpoint]:
    """Scan pages/api/**/*.js and app/api/**/route.{js,ts} for Next.js routes."""
    endpoints: list[Endpoint] = []

    # Pages Router: pages/api/**/*.js -> /api/<name>
    pages_api = root / "pages" / "api"
    if pages_api.is_dir():
        for file in pages_api.rglob("*"):
            if file.suffix not in (".js", ".ts", ".jsx", ".tsx"):
                continue
            if any(part in _SKIP_DIRS for part in file.parts):
                continue
            # Convert path to route
            rel = file.relative_to(pages_api)
            parts = list(rel.parts)
            # Remove extension from last part
            parts[-1] = re.sub(r"\.[jt]sx?$", "", parts[-1])
            if parts[-1] == "index":
                parts = parts[:-1]
            route_path = "/api/" + "/".join(parts)
            # Replace [param] with {param}
            route_path = re.sub(r"\[([^\]]+)\]", r"{\1}", route_path)

            # Detect methods from file content
            try:
                content = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = ""

            methods = _detect_nextjs_methods(content)
            handler_file = str(file.relative_to(root))

            for method in methods:
                endpoints.append(
                    Endpoint(
                        method=method,
                        path=route_path,
                        handler_file=handler_file,
                        params=[],
                    )
                )
            if not methods:
                endpoints.append(
                    Endpoint(
                        method="GET",
                        path=route_path,
                        handler_file=handler_file,
                        params=[],
                    )
                )

    # App Router: app/api/**/route.{js,ts} -> /api/<path>
    app_api = root / "app" / "api"
    if app_api.is_dir():
        for file in app_api.rglob("route.*"):
            if file.suffix not in (".js", ".ts"):
                continue
            rel = file.parent.relative_to(app_api)
            route_path = "/api/" + "/".join(rel.parts)
            endpoints.append(
                Endpoint(
                    method="GET",
                    path=route_path,
                    handler_file=str(file.relative_to(root)),
                    params=[],
                )
            )

    return endpoints


def _detect_nextjs_methods(content: str) -> list[str]:
    """Detect HTTP methods handled by a Next.js API route handler."""
    methods: list[str] = []
    # Check for req.method comparisons like: req.method === 'GET'
    found = re.findall(r"req\.method\s*[=!]=+\s*['\"]([A-Z]+)['\"]", content)
    methods.extend(found)
    # Check Allow header: res.setHeader('Allow', ['GET', 'POST'])
    allow_match = re.search(r"setHeader\s*\(\s*['\"]Allow['\"],\s*\[([^\]]+)\]", content)
    if allow_match:
        allowed = re.findall(r"['\"]([A-Z]+)['\"]", allow_match.group(1))
        for m in allowed:
            if m not in methods:
                methods.append(m)
    return methods or ["GET"]


# ---------------------------------------------------------------------------
# Python file scanning
# ---------------------------------------------------------------------------


def _scan_python_file(path: Path, root: Path) -> tuple[list[Endpoint], list[CLICommand]]:
    """Scan a Python file for Flask/FastAPI routes and Click/argparse commands."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], []

    endpoints: list[Endpoint] = []
    cli_commands: list[CLICommand] = []
    rel_path = str(path.relative_to(root))

    # Flask routes
    for m in _FLASK_ROUTE_RE.finditer(content):
        route_path = m.group(1)
        methods_str = m.group(2) or ""
        if methods_str:
            methods = [
                mth.strip().strip('"\'').upper()
                for mth in methods_str.split(",")
                if mth.strip().strip('"\'')
            ]
        else:
            methods = ["GET"]
        for method in methods:
            endpoints.append(
                Endpoint(method=method, path=route_path, handler_file=rel_path, params=[])
            )

    # FastAPI routes
    for m in _FASTAPI_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        route_path = m.group(2)
        endpoints.append(
            Endpoint(method=method, path=route_path, handler_file=rel_path, params=[])
        )

    # Django urls.py
    if path.name in ("urls.py",):
        for m in _DJANGO_URL_RE.finditer(content):
            route_path = "/" + m.group(1).lstrip("/")
            endpoints.append(
                Endpoint(method="GET", path=route_path, handler_file=rel_path, params=[])
            )
        for m in _DJANGO_RE_PATH_RE.finditer(content):
            route_path = "/" + m.group(1).lstrip("/").lstrip("^").rstrip("$")
            endpoints.append(
                Endpoint(method="GET", path=route_path, handler_file=rel_path, params=[])
            )

    # Click commands: look for @cli.command() / @click.command() decorators
    # Pattern: @something.command() or @click.command() followed by def name():
    click_cmd_re = re.compile(
        r'@(?:\w+)\.command\(\s*(?:["\']([^"\']*)["\'])?\s*\)\s*\n'
        r'(?:@[^\n]+\n)*'  # skip additional decorators
        r'\s*def\s+([a-z_][a-z0-9_]*)\s*\([^)]*\)\s*(?:->\s*\S+\s*)?:\s*\n'
        r'\s*(?:"""([^"]*?)""")?',
        re.DOTALL,
    )
    for m in click_cmd_re.finditer(content):
        cmd_name = m.group(1) or m.group(2)
        description = (m.group(3) or "").strip().split("\n")[0]
        cli_commands.append(
            CLICommand(name=cmd_name, description=description or None, handler_file=rel_path)
        )

    # argparse subparsers
    for m in _ARGPARSE_ADD_PARSER.finditer(content):
        cmd_name = m.group(1)
        description = m.group(2)
        cli_commands.append(
            CLICommand(name=cmd_name, description=description, handler_file=rel_path)
        )

    return endpoints, cli_commands


# ---------------------------------------------------------------------------
# JS/TS file scanning
# ---------------------------------------------------------------------------


def _scan_js_file(path: Path, root: Path) -> list[Endpoint]:
    """Scan a JS/TS file for Express.js routes."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    endpoints: list[Endpoint] = []
    rel_path = str(path.relative_to(root))

    for m in _EXPRESS_ROUTE_RE.finditer(content):
        method = m.group(1).upper()
        route_path = m.group(2)
        endpoints.append(
            Endpoint(method=method, path=route_path, handler_file=rel_path, params=[])
        )

    return endpoints


# ---------------------------------------------------------------------------
# Undocumented route detection
# ---------------------------------------------------------------------------


def _count_undocumented(endpoints: list[Endpoint], root: Path) -> int:
    """Count endpoints that appear to lack docstrings in their handler functions."""
    undocumented = 0
    for ep in endpoints:
        handler_path = root / ep.handler_file
        if not handler_path.exists():
            continue
        try:
            content = handler_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Check if the file has at least some docstrings
        if '"""' not in content and "'''" not in content:
            undocumented += 1
    return undocumented


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze(repo_path: str) -> APIReport:
    """Analyze the API surface of repo_path and return an APIReport."""
    root = Path(repo_path).resolve()

    all_endpoints: list[Endpoint] = []
    all_cli_commands: list[CLICommand] = []

    # Scan Python files
    for path in sorted(root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        eps, cmds = _scan_python_file(path, root)
        all_endpoints.extend(eps)
        all_cli_commands.extend(cmds)

    # Scan JS/TS files (Express)
    for path in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in (".js", ".ts", ".jsx", ".tsx"):
            continue
        # Skip Next.js pages/api (handled separately)
        if "pages" in path.parts and "api" in path.parts:
            continue
        all_endpoints.extend(_scan_js_file(path, root))

    # Next.js API routes
    all_endpoints.extend(_extract_nextjs_routes(root))

    # Determine api_type
    has_http = bool(all_endpoints)
    has_cli = bool(all_cli_commands)

    if has_http and has_cli:
        api_type = "mixed"
    elif has_cli:
        api_type = "cli"
    elif has_http:
        api_type = "rest"
    else:
        # Check for setup.py / pyproject (library)
        if (root / "setup.py").exists() or (root / "pyproject.toml").exists():
            api_type = "library"
        else:
            api_type = "rest"

    # Undocumented routes: rough estimate
    undocumented = 0
    handler_files_seen: set[str] = set()
    for ep in all_endpoints:
        if ep.handler_file not in handler_files_seen:
            handler_files_seen.add(ep.handler_file)
            handler_path = root / ep.handler_file
            if handler_path.exists():
                try:
                    content = handler_path.read_text(encoding="utf-8", errors="replace")
                    if '"""' not in content and "'''" not in content:
                        undocumented += len([e for e in all_endpoints if e.handler_file == ep.handler_file])
                except OSError:
                    pass

    return APIReport(
        api_type=api_type,
        endpoints=all_endpoints,
        graphql_types=None,
        cli_commands=all_cli_commands if all_cli_commands else None,
        public_exports=[],
        total_routes=len(all_endpoints),
        undocumented_routes=undocumented,
    )

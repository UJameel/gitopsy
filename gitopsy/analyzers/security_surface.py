"""Security Surface Scanner — detects secrets, injection risks, and auth patterns."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from gitopsy.models.schemas import SecurityFinding, SecurityReport

_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rb", ".env", ".yml", ".yaml", ".json", ".sh", ".env.example",
}

# ---------------------------------------------------------------------------
# Secret detection patterns
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "critical"),
    ("aws-secret", re.compile(r"(?i)aws[_\-. ]?secret[_\-. ]?access[_\-. ]?key\s*[=:]\s*\S+"), "critical"),
    ("generic-api-key", re.compile(r"""(?i)(?:api[_\-. ]?key|apikey)\s*[=:]\s*['"][a-zA-Z0-9_\-]{16,}['"]"""), "high"),
    ("generic-password", re.compile(r"""(?i)(?:password|passwd|pwd)\s*[=:]\s*['"][^'"]{6,}['"]"""), "high"),
    ("private-key-header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "critical"),
    ("secret-key", re.compile(r"""(?i)(?:secret[_\-. ]?key|secretkey)\s*[=:]\s*['"][^'"]{6,}['"]"""), "high"),
    ("github-token", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"), "critical"),
    ("jwt-secret", re.compile(r"""(?i)jwt[_\-. ]?secret\s*[=:]\s*['"][^'"]{6,}['"]"""), "high"),
]

# ---------------------------------------------------------------------------
# SQL injection patterns
# ---------------------------------------------------------------------------

_SQL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    # String % formatting with SQL keywords
    re.compile(r"""(?i)(?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM)\s.*?['"]\s*%\s*\w"""),
    re.compile(r"""(?i)["']\s*\+\s*\w+\s*\+\s*["']\s*.*(?:SELECT|WHERE|FROM|INSERT|UPDATE|DELETE)"""),
    # f-string in SQL context
    re.compile(r"""(?i)f['"](?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM).*\{"""),
    # String format with SQL
    re.compile(r"""(?i)["'].*(?:SELECT|WHERE|FROM).*['"]\.format\("""),
    # Direct % formatting: "... WHERE name = '%s'" % variable
    re.compile(r"""(?i)["'].*(?:WHERE|SELECT|FROM|INSERT|UPDATE|DELETE)[^'"]*['"][^)]*%\s+\w"""),
]

# ---------------------------------------------------------------------------
# Auth pattern detection
# ---------------------------------------------------------------------------

_AUTH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("jwt", re.compile(r"""(?i)\bimport\s+jwt\b|\bfrom\s+(?:jwt|jose|pyjwt)\b|require\s*\(\s*['"]jsonwebtoken['"]""")),
    ("flask-login", re.compile(r"""(?i)\bfrom\s+flask_login\b|\bimport\s+flask_login\b""")),
    ("express-session", re.compile(r"""(?i)require\s*\(\s*['"]express-session['"]""")),
    ("oauth", re.compile(r"""(?i)\boauth\b|\bauthlib\b|\bpassport\b""")),
    ("basic-auth", re.compile(r"""(?i)basic[_\-. ]?auth|Authorization.*Basic""")),
]

# ---------------------------------------------------------------------------
# CORS patterns
# ---------------------------------------------------------------------------

_CORS_WILDCARD_RE = re.compile(
    r"""(?i)(?:Access-Control-Allow-Origin['":\s]+[*]|CORS\s*\([^)]*\)|cors\s*\(\s*\{[^}]*origin[^}]*\*[^}]*\})"""
)

# ---------------------------------------------------------------------------
# Docker port detection
# ---------------------------------------------------------------------------


def _extract_docker_ports(root: Path) -> list[int]:
    """Extract exposed host ports from docker-compose.yml."""
    compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
    ports: list[int] = []

    for fname in compose_files:
        compose_path = root / fname
        if not compose_path.exists():
            continue
        try:
            content = compose_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Match port mappings: '8080:80' or "8080:80" or just 8080
        for m in re.finditer(r"""['"]?(\d+):(\d+)['"]?""", content):
            host_port = int(m.group(1))
            container_port = int(m.group(2))
            ports.append(host_port)
            if container_port not in ports:
                ports.append(container_port)
        # Also match bare port: - "8080"
        for m in re.finditer(r"""['"](\d{2,5})['"]""", content):
            p = int(m.group(1))
            if 1 <= p <= 65535 and p not in ports:
                ports.append(p)

    return sorted(set(ports))


# ---------------------------------------------------------------------------
# .env file detection
# ---------------------------------------------------------------------------


def _check_env_files(root: Path) -> tuple[list[SecurityFinding], list[str]]:
    """Check if .env files exist and are not protected by .gitignore."""
    findings: list[SecurityFinding] = []
    env_in_git: list[str] = []

    # Check if .env exists
    env_file = root / ".env"
    if env_file.exists():
        # Check .gitignore
        gitignore = root / ".gitignore"
        protected = False
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8", errors="replace")
            if ".env" in content:
                protected = True

        if not protected:
            rel_path = ".env"
            findings.append(
                SecurityFinding(
                    severity="high",
                    category="env-file-exposed",
                    file=rel_path,
                    line=None,
                    description=".env file exists but is not listed in .gitignore — secrets may be committed to git",
                )
            )
            env_in_git.append(rel_path)

    # Also check via git log (if git repo)
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--full-history", "--", "*.env", ".env"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            if ".env" not in env_in_git:
                env_in_git.append(".env")
            findings.append(
                SecurityFinding(
                    severity="critical",
                    category="env-file-in-git",
                    file=".env",
                    line=None,
                    description=".env file appears in git history — secrets may have been committed",
                )
            )
    except Exception:
        pass

    return findings, env_in_git


# ---------------------------------------------------------------------------
# Source file scanning
# ---------------------------------------------------------------------------


def _scan_file_for_secrets(
    path: Path, root: Path
) -> list[SecurityFinding]:
    """Scan a file for hardcoded secrets."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[SecurityFinding] = []
    rel_path = str(path.relative_to(root))
    lines = content.splitlines()

    for pattern_name, pattern, severity in _SECRET_PATTERNS:
        for m in pattern.finditer(content):
            # Find line number
            line_no = content[: m.start()].count("\n") + 1
            findings.append(
                SecurityFinding(
                    severity=severity,
                    category="hardcoded-secret",
                    file=rel_path,
                    line=line_no,
                    description=f"Potential {pattern_name} detected: {m.group(0)[:60]}",
                )
            )

    return findings


def _scan_file_for_sql_injection(
    path: Path, root: Path
) -> list[SecurityFinding]:
    """Scan a Python/JS file for SQL injection patterns."""
    if path.suffix not in (".py", ".js", ".ts", ".php"):
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[SecurityFinding] = []
    rel_path = str(path.relative_to(root))

    for pattern in _SQL_INJECTION_PATTERNS:
        for m in pattern.finditer(content):
            line_no = content[: m.start()].count("\n") + 1
            findings.append(
                SecurityFinding(
                    severity="medium",
                    category="sql-injection",
                    file=rel_path,
                    line=line_no,
                    description=f"Potential SQL injection via string formatting: {m.group(0)[:80]}",
                )
            )

    return findings


def _detect_auth_pattern(root: Path) -> str | None:
    """Detect the authentication pattern used in the codebase."""
    for path in sorted(root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern_name, pattern in _AUTH_PATTERNS:
            if pattern.search(content):
                return pattern_name

    for path in sorted(root.rglob("*.js")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern_name, pattern in _AUTH_PATTERNS:
            if pattern.search(content):
                return pattern_name

    return None


# ---------------------------------------------------------------------------
# Risk level computation
# ---------------------------------------------------------------------------


def _compute_risk_level(
    secrets_found: int,
    env_in_git: list[str],
    findings: list[SecurityFinding],
) -> str:
    if secrets_found > 0:
        return "critical"
    if env_in_git:
        return "high"
    severities = {f.severity for f in findings}
    if "critical" in severities:
        return "critical"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def _generate_recommendations(
    findings: list[SecurityFinding],
    auth_pattern: str | None,
    exposed_ports: list[int],
) -> list[str]:
    recs: list[str] = []
    categories = {f.category for f in findings}

    if "hardcoded-secret" in categories:
        recs.append("Move all secrets to environment variables or a secrets manager")
    if "env-file-exposed" in categories or "env-file-in-git" in categories:
        recs.append("Add .env to .gitignore and rotate any exposed credentials")
    if "sql-injection" in categories:
        recs.append("Use parameterized queries or an ORM instead of string-formatted SQL")
    if not auth_pattern:
        recs.append("Consider adding authentication to protect API endpoints")
    if 80 in exposed_ports or 8080 in exposed_ports:
        recs.append("Consider using HTTPS (port 443) instead of plain HTTP for production")
    if not recs:
        recs.append("No critical issues found — continue to follow security best practices")

    return recs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze(repo_path: str) -> SecurityReport:
    """Analyze the security surface of repo_path and return a SecurityReport."""
    root = Path(repo_path).resolve()

    all_findings: list[SecurityFinding] = []
    secrets_found = 0

    # Scan source files
    for path in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        # Secrets
        secret_findings = _scan_file_for_secrets(path, root)
        all_findings.extend(secret_findings)
        secrets_found += len(secret_findings)

        # SQL injection
        sql_findings = _scan_file_for_sql_injection(path, root)
        all_findings.extend(sql_findings)

    # .env file checks
    env_findings, env_in_git = _check_env_files(root)
    all_findings.extend(env_findings)

    # Docker ports
    exposed_ports = _extract_docker_ports(root)

    # Auth pattern
    auth_pattern = _detect_auth_pattern(root)

    # Risk level
    risk_level = _compute_risk_level(secrets_found, env_in_git, all_findings)

    # Recommendations
    recommendations = _generate_recommendations(all_findings, auth_pattern, exposed_ports)

    return SecurityReport(
        risk_level=risk_level,
        findings=all_findings,
        secrets_found=secrets_found,
        env_files_in_git=env_in_git,
        exposed_ports=exposed_ports,
        auth_pattern=auth_pattern,
        recommendations=recommendations,
    )

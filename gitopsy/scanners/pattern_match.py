"""Regex-based pattern matching utilities for import parsing, secret detection, etc."""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Import patterns
# ---------------------------------------------------------------------------

# Python: `import foo`, `import foo.bar`, `from foo import bar`
_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))",
    re.MULTILINE,
)

# JavaScript / TypeScript:
#   import X from 'y'
#   import { X } from "y"
#   import * as X from 'y'
#   require('y')
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w*{}\s,"']+\s+from\s+)?['"]([@\w/.-]+)['"]|require\(['"]([@\w/.-]+)['"]\))""",
    re.MULTILINE,
)


def find_python_imports(code: str) -> list[str]:
    """Extract module names from Python import statements.

    Returns a deduplicated list of top-level module names.
    """
    if not code:
        return []

    modules: set[str] = set()
    for match in _PY_IMPORT_RE.finditer(code):
        from_module = match.group(1)
        import_modules = match.group(2)

        if from_module:
            # `from foo.bar import ...` → "foo"
            top = from_module.lstrip(".").split(".")[0]
            if top:
                modules.add(top)
        elif import_modules:
            # `import foo, bar.baz` → "foo", "bar"
            for part in import_modules.split(","):
                top = part.strip().split(".")[0]
                if top:
                    modules.add(top)

    return sorted(modules)


def find_javascript_imports(code: str) -> list[str]:
    """Extract module names from JavaScript/TypeScript import statements.

    Returns a deduplicated list of module specifiers.
    """
    if not code:
        return []

    modules: set[str] = set()
    for match in _JS_IMPORT_RE.finditer(code):
        specifier = match.group(1) or match.group(2)
        if specifier:
            # Skip relative imports (./, ../)
            if not specifier.startswith("."):
                # For scoped packages like @babel/core → keep as-is for top-level
                modules.add(specifier)

    return sorted(modules)


# ---------------------------------------------------------------------------
# Secret detection
# ---------------------------------------------------------------------------

@dataclass
class SecretFinding:
    """A potential hardcoded secret found in source code."""

    pattern_name: str
    line_number: int
    snippet: str  # Redacted snippet


# Patterns that suggest hardcoded secrets
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws[_\s]secret[_\s](?:access[_\s])?key\s*[=:]\s*[\"'][^\"']{10,}[\"']")),
    ("generic_api_key", re.compile(r"(?i)(?:api[_\s]?key|apikey)\s*[=:]\s*[\"'][A-Za-z0-9_\-]{8,}[\"']")),
    ("generic_secret", re.compile(r"(?i)(?:secret[_\s]?key|secret)\s*[=:]\s*[\"'][A-Za-z0-9_\-]{8,}[\"']")),
    ("private_key_header", re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----")),
    ("password_assignment", re.compile(r"(?i)\bpassword\s*[=:]\s*[\"'][^\"']{6,}[\"']")),
    ("token_assignment", re.compile(r"(?i)\b(?:access[_\s]token|auth[_\s]token|bearer[_\s]token)\s*[=:]\s*[\"'][^\"']{10,}[\"']")),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9]{10,}-[0-9A-Za-z]+")),
]

# Patterns that indicate the value is from the environment (safe)
_SAFE_PATTERNS = [
    re.compile(r"os\.environ"),
    re.compile(r"os\.getenv"),
    re.compile(r"process\.env"),
    re.compile(r"getenv\("),
    re.compile(r"environ\.get\("),
    re.compile(r"your[_\s-]"),
    re.compile(r"<[^>]+>"),  # placeholder like <YOUR_KEY>
    re.compile(r"\$\{"),  # template variable
]


def _is_likely_safe(line: str) -> bool:
    """Return True if the line looks like a safe env-based reference."""
    return any(p.search(line) for p in _SAFE_PATTERNS)


def detect_secret_patterns(code: str) -> list[SecretFinding]:
    """Scan code for patterns that look like hardcoded secrets.

    Returns a list of SecretFinding objects (may be empty).
    """
    if not code:
        return []

    findings: list[SecretFinding] = []
    lines = code.splitlines()

    for lineno, line in enumerate(lines, start=1):
        if _is_likely_safe(line):
            continue
        for name, pattern in _SECRET_PATTERNS:
            if pattern.search(line):
                # Produce a short redacted snippet
                snippet = line.strip()[:80]
                findings.append(
                    SecretFinding(
                        pattern_name=name,
                        line_number=lineno,
                        snippet=snippet,
                    )
                )
                break  # one finding per line

    return findings


# ---------------------------------------------------------------------------
# TODO / FIXME / HACK detection
# ---------------------------------------------------------------------------

@dataclass
class TodoComment:
    """A TODO / FIXME / HACK comment found in source code."""

    kind: str  # "TODO", "FIXME", "HACK", "XXX", "NOTE"
    line_number: int
    text: str


_TODO_RE = re.compile(
    r"#\s*(?P<kind>TODO|FIXME|HACK|XXX|NOTE)\s*:?\s*(?P<text>.*)",
    re.IGNORECASE,
)


def find_todo_comments(code: str) -> list[TodoComment]:
    """Find TODO/FIXME/HACK style comments in source code."""
    if not code:
        return []

    results: list[TodoComment] = []
    for lineno, line in enumerate(code.splitlines(), start=1):
        m = _TODO_RE.search(line)
        if m:
            results.append(
                TodoComment(
                    kind=m.group("kind").upper(),
                    line_number=lineno,
                    text=m.group("text").strip(),
                )
            )
    return results

# Gitopsy — Codebase Intelligence

When the user runs `/gitopsy`, analyze their current repository and produce a comprehensive HTML report.

## Instructions

1. Check if gitopsy is installed: `python -m gitopsy --version`
2. If not installed, install it: `pip install gitopsy` (or `pip install -e /path/to/gitopsy` if running from source)
3. Determine the repo path (default: current working directory)
4. Run: `python -m gitopsy . --output gitopsy-report.html`
5. Report the output path to the user
6. Optionally, display a summary of key findings from `--json` output

## Usage

- `/gitopsy` — analyze current directory
- `/gitopsy /path/to/repo` — analyze specific repo
- `/gitopsy --analyzers arch,debt` — run specific analyzers only

## Analyzers

| Name | Flag | Description |
|------|------|-------------|
| Architecture | `arch` | Project structure, layers, entry points |
| Tech Debt | `debt` | Code quality score, hotspots, recommendations |
| Onboarding | `onboarding` | Setup guide, key files, contributors |
| Dependencies | `deps` | Package versions, licenses, risk score |
| Conventions | `conventions` | Naming, formatting, consistency score |
| API Extractor | `api` | HTTP routes, CLI commands, public exports |
| Security | `security` | Secrets, SQL injection, auth patterns |
| Setup Guide | `setup` | Prerequisites, install steps, env vars |

## Output

The report is a single self-contained HTML file with:
- Score dashboard showing health grade for each analyzer
- 8 interactive tabs with detailed findings
- Dark theme with searchable tables and copy buttons
- Charts for language breakdown and tech debt dimensions

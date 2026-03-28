# Gitopsy

> *Dissect any codebase in seconds.*

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![PyPI](https://img.shields.io/pypi/v/gitopsy)

Gitopsy is an open-source codebase intelligence engine that deeply analyzes any repository and produces a beautiful, interactive HTML report covering architecture, tech debt, and onboarding — everything a developer needs to understand an unfamiliar codebase.

<!-- screenshot placeholder -->
<!-- ![Gitopsy Report Screenshot](docs/examples/screenshots/overview.png) -->

## Features

- **Architecture Analyzer** — framework detection, project type, entry points, layer structure, dependency graph, language breakdown
- **Tech Debt Scorer** — 7-dimension scoring (TODO density, test coverage, complexity hotspots, documentation gaps, and more)
- **Onboarding Guide** — auto-generated "how to get started" guide from README, Makefile, contributors
- **Beautiful HTML Report** — dark-themed, self-contained, 3-tab report with Chart.js visualizations
- **Zero mandatory external API calls** — works completely offline
- **Git-optional** — works on any directory; git history enables bonus features

## Installation

```bash
pip install gitopsy
```

Or install from source:

```bash
git clone https://github.com/gitopsy/gitopsy
cd gitopsy
pip install -e ".[dev]"
```

## Usage

```bash
# Analyze the current directory
gitopsy .

# Analyze any repository
gitopsy /path/to/repo

# Custom output path
gitopsy . --output report.html

# Run specific analyzers only
gitopsy . --analyzers arch,debt

# Output raw JSON (for piping or scripting)
gitopsy . --json

# Use as a Python module
python -m gitopsy /path/to/repo
```

## Python API

```python
from gitopsy.orchestrator import analyze
from gitopsy.report.renderer import render

report = analyze("/path/to/repo")
render(report, "/tmp/report.html")

# Or get the raw data
print(report.architecture.framework)  # "flask"
print(report.tech_debt.grade)         # "B"
print(report.tech_debt.overall_score) # 35
```

## Report Tabs

| Tab | What you get |
|-----|-------------|
| **Architecture** | Project type, framework, language breakdown chart, entry points, layers, key files, internal dep graph |
| **Tech Debt** | Overall grade (A-F), 7-dimension scoring chart, complexity hotspots, recommendations |
| **Onboarding** | Project summary, key files to read, setup steps, test commands, contributors, gotchas |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to run tests and add new analyzers.

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

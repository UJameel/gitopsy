# Contributing to Gitopsy

Thank you for your interest in contributing to Gitopsy!

## Development Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/gitopsy/gitopsy
   cd gitopsy
   ```

2. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Run the tests:**
   ```bash
   pytest
   ```

4. **Run against a real repo:**
   ```bash
   gitopsy /path/to/any/repo --output /tmp/report.html
   ```

## Project Structure

```
gitopsy/
├── gitopsy/
│   ├── analyzers/      # One file per analyzer
│   ├── scanners/       # Low-level file system utilities
│   ├── models/         # Pydantic schemas
│   ├── report/         # HTML rendering (Jinja2 + Chart.js)
│   ├── orchestrator.py # Chains analyzers
│   └── cli.py          # Click CLI
└── tests/
    ├── fixtures/        # Minimal fake repos for testing
    └── test_*.py        # Test files (written before implementation)
```

## Adding a New Analyzer

1. **Write tests first** (`tests/test_myanalyzer.py`) — TDD is required
2. **Create the schema** in `gitopsy/models/schemas.py` if needed
3. **Implement the analyzer** in `gitopsy/analyzers/myanalyzer.py`:
   ```python
   def analyze(repo_path: str) -> MyReport:
       ...
   ```
4. **Wire it into the orchestrator** (`gitopsy/orchestrator.py`)
5. **Add a tab** to `gitopsy/report/template.html`

## Guidelines

- All Python code must have type hints
- Use Pydantic v2 syntax (`model_config`, `ConfigDict`)
- No mandatory external network calls — all analysis must work offline
- Tests must be written **before** implementation (TDD)
- All public functions must have docstrings

## Running Tests with Coverage

```bash
pytest --cov=gitopsy --cov-report=term-missing
```

## Code Style

- Follow PEP 8
- Use type hints everywhere
- Prefer `pathlib.Path` over `os.path`
- Handle errors gracefully — never let an analyzer crash the entire pipeline

## Submitting a Pull Request

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-analyzer`)
3. Write tests, implement, verify all tests pass
4. Open a PR with a clear description of what was added/changed

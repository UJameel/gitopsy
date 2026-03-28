"""Click-based CLI interface for Gitopsy."""

from __future__ import annotations

import sys
from pathlib import Path

import click


@click.command("gitopsy")
@click.argument("repo_path", default=".", required=False)
@click.option(
    "--output",
    "-o",
    default="gitopsy-report.html",
    show_default=True,
    help="Output HTML file path.",
)
@click.option(
    "--analyzers",
    default=None,
    help="Comma-separated analyzers to run: arch,debt,onboarding (default: all).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output raw JSON to stdout instead of HTML.",
)
def main(
    repo_path: str,
    output: str,
    analyzers: str | None,
    output_json: bool,
) -> None:
    """Gitopsy — dissect any codebase in seconds.

    Analyzes REPO_PATH (default: current directory) and writes an HTML report.

    \b
    Examples:
        gitopsy .
        gitopsy /path/to/repo --output report.html
        gitopsy . --analyzers arch,debt
        gitopsy . --json
    """
    # Validate path
    path = Path(repo_path).resolve()
    if not path.exists():
        click.echo(f"Error: path does not exist: {path}", err=True)
        sys.exit(1)
    if not path.is_dir():
        click.echo(f"Error: path is not a directory: {path}", err=True)
        sys.exit(1)

    # Parse analyzer list
    analyzer_list: list[str] | None = None
    if analyzers:
        analyzer_list = [a.strip() for a in analyzers.split(",")]

    click.echo(f"Analyzing {path} ...")

    from gitopsy.orchestrator import analyze as run_analyze
    from gitopsy.report.renderer import render

    report = run_analyze(str(path), analyzer_list)

    if output_json:
        click.echo(report.model_dump_json(indent=2))
    else:
        out_path = str(Path(output).resolve())
        click.echo(f"Generating report → {out_path}")
        render(report, out_path)
        click.echo(f"Done. Open {out_path} in your browser.")

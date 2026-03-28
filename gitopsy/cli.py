"""Click-based CLI interface for Gitopsy."""

from __future__ import annotations

import sys
from pathlib import Path

import click


@click.group(invoke_without_command=True)
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
@click.option(
    "--save-json",
    "save_json",
    is_flag=True,
    default=False,
    help="Also write a .json snapshot alongside the HTML report.",
)
@click.option(
    "--badge",
    "write_badge",
    is_flag=True,
    default=False,
    help="Write a gitopsy-badge.svg alongside the HTML report.",
)
@click.pass_context
def main(
    ctx: click.Context,
    repo_path: str,
    output: str,
    analyzers: str | None,
    output_json: bool,
    save_json: bool,
    write_badge: bool,
) -> None:
    """Gitopsy — dissect any codebase in seconds.

    Analyzes REPO_PATH (default: current directory) and writes an HTML report.

    \b
    Examples:
        gitopsy .
        gitopsy /path/to/repo --output report.html
        gitopsy . --analyzers arch,debt
        gitopsy . --json
        gitopsy . --badge
    """
    # If a subcommand was invoked, let it handle everything.
    if ctx.invoked_subcommand is not None:
        return

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
        return

    out_path = str(Path(output).resolve())
    click.echo(f"Generating report → {out_path}")
    render(report, out_path)

    if save_json:
        json_path = str(Path(output).with_suffix(".json").resolve())
        Path(json_path).write_text(report.model_dump_json(indent=2), encoding="utf-8")
        click.echo(f"JSON snapshot → {json_path}")

    if write_badge:
        from gitopsy.report.badge import generate_badge
        grade = (report.tech_debt.grade if report.tech_debt else "N/A")
        score = (report.tech_debt.overall_score if report.tech_debt else 0)
        badge_path = str(Path(output).parent / "gitopsy-badge.svg")
        Path(badge_path).write_text(generate_badge(grade, score), encoding="utf-8")
        click.echo(f"Badge → {badge_path}")

    click.echo(f"Done. Open {out_path} in your browser.")


@main.command("badge")
@click.argument("repo_path", default=".")
@click.option(
    "--output",
    "-o",
    default="gitopsy-badge.svg",
    show_default=True,
    help="Output SVG path.",
)
def badge_cmd(repo_path: str, output: str) -> None:
    """Generate a Gitopsy grade badge SVG."""
    path = Path(repo_path).resolve()
    if not path.exists():
        click.echo(f"Error: path does not exist: {path}", err=True)
        sys.exit(1)
    if not path.is_dir():
        click.echo(f"Error: path is not a directory: {path}", err=True)
        sys.exit(1)

    click.echo(f"Analyzing {path} for badge ...")

    from gitopsy.orchestrator import analyze as run_analyze
    from gitopsy.report.badge import generate_badge

    report = run_analyze(str(path), ["debt"])
    grade = report.tech_debt.grade if report.tech_debt else "N/A"
    score = report.tech_debt.overall_score if report.tech_debt else 0

    svg = generate_badge(grade, score)
    out_path = str(Path(output).resolve())
    Path(out_path).write_text(svg, encoding="utf-8")
    click.echo(f"Badge written → {out_path}")


@main.command("diff")
@click.argument("old_report", type=click.Path(exists=True, dir_okay=False))
@click.argument("new_report", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--output",
    "-o",
    default="gitopsy-diff.html",
    show_default=True,
    help="Output HTML diff report path.",
)
def diff_cmd(old_report: str, new_report: str, output: str) -> None:
    """Compare two Gitopsy JSON snapshots and render a diff report.

    \b
    Example:
        gitopsy . --save-json          # capture snapshot.json
        # ... make changes ...
        gitopsy . --save-json --output new.html
        gitopsy diff gitopsy-report.json new.json
    """
    import json

    from gitopsy.models.schemas import GitopsyReport
    from gitopsy.report.diff import compare, render_diff

    old_data = json.loads(Path(old_report).read_text(encoding="utf-8"))
    new_data = json.loads(Path(new_report).read_text(encoding="utf-8"))

    old = GitopsyReport.model_validate(old_data)
    new = GitopsyReport.model_validate(new_data)

    diff = compare(old, new)
    out_path = str(Path(output).resolve())
    render_diff(diff, out_path)
    click.echo(f"Diff report → {out_path}")

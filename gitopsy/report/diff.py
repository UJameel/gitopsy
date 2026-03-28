"""Diff and comparison logic for two Gitopsy reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gitopsy.models.schemas import GitopsyReport


def compare(old: GitopsyReport, new: GitopsyReport) -> dict[str, Any]:
    """Compare two GitopsyReport objects and return a diff summary.

    Args:
        old: The baseline report (earlier snapshot).
        new: The new report (later snapshot).

    Returns:
        A dict with keys:
            old_project:        project name from old report
            new_project:        project name from new report
            old_generated_at:   timestamp of old report
            new_generated_at:   timestamp of new report
            grade_change:       tuple (old_grade, new_grade) or None if unavailable
            grade_improved:     True if grade letter improved
            score_change:       int delta (new_score - old_score), or None
            new_findings:       list of SecurityFinding dicts added in new report
            resolved_findings:  list of SecurityFinding dicts removed from new report
            new_files:          list of new key file paths
            deleted_files:      list of removed key file paths
            new_recommendations: list of new recommendations
            resolved_recommendations: list of removed recommendations
    """
    diff: dict[str, Any] = {
        "old_project": old.project_name,
        "new_project": new.project_name,
        "old_generated_at": old.generated_at,
        "new_generated_at": new.generated_at,
        "grade_change": None,
        "grade_improved": False,
        "score_change": None,
        "new_findings": [],
        "resolved_findings": [],
        "new_files": [],
        "deleted_files": [],
        "new_recommendations": [],
        "resolved_recommendations": [],
    }

    # Grade / score comparison
    _grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
    old_grade = old.tech_debt.grade if old.tech_debt else None
    new_grade = new.tech_debt.grade if new.tech_debt else None
    old_score = old.tech_debt.overall_score if old.tech_debt else None
    new_score = new.tech_debt.overall_score if new.tech_debt else None

    if old_grade and new_grade:
        diff["grade_change"] = (old_grade, new_grade)
        diff["grade_improved"] = _grade_order.get(new_grade, 0) > _grade_order.get(old_grade, 0)

    if old_score is not None and new_score is not None:
        diff["score_change"] = new_score - old_score

    # Security findings diff
    def finding_key(f: Any) -> str:
        return f"{f.severity}:{f.category}:{f.file}:{f.line}:{f.description}"

    old_findings = {finding_key(f): f for f in (old.security.findings if old.security else [])}
    new_findings_map = {finding_key(f): f for f in (new.security.findings if new.security else [])}

    diff["new_findings"] = [
        _finding_to_dict(f)
        for k, f in new_findings_map.items()
        if k not in old_findings
    ]
    diff["resolved_findings"] = [
        _finding_to_dict(f)
        for k, f in old_findings.items()
        if k not in new_findings_map
    ]

    # Key file diff (from architecture)
    old_files = {kf.path for kf in (old.architecture.key_files if old.architecture else [])}
    new_files = {kf.path for kf in (new.architecture.key_files if new.architecture else [])}
    diff["new_files"] = sorted(new_files - old_files)
    diff["deleted_files"] = sorted(old_files - new_files)

    # Recommendations diff
    old_recs = set(old.tech_debt.recommendations if old.tech_debt else [])
    new_recs = set(new.tech_debt.recommendations if new.tech_debt else [])
    diff["new_recommendations"] = sorted(new_recs - old_recs)
    diff["resolved_recommendations"] = sorted(old_recs - new_recs)

    return diff


def _finding_to_dict(finding: Any) -> dict[str, Any]:
    """Convert a SecurityFinding to a plain dict."""
    return {
        "severity": finding.severity,
        "category": finding.category,
        "file": finding.file,
        "line": finding.line,
        "description": finding.description,
    }


_DIFF_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gitopsy Diff Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 24px; background: #f9fafb; color: #111; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
    .meta {{ color: #666; font-size: 0.85rem; margin-bottom: 24px; }}
    .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
    .card h2 {{ margin: 0 0 12px; font-size: 1.1rem; }}
    .grade-row {{ display: flex; gap: 24px; align-items: center; }}
    .grade-badge {{ font-size: 2rem; font-weight: bold; padding: 8px 16px; border-radius: 6px; }}
    .arrow {{ font-size: 1.5rem; color: #999; }}
    .improved {{ color: #16a34a; }}
    .regressed {{ color: #dc2626; }}
    .unchanged {{ color: #6b7280; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e5e7eb; }}
    th {{ background: #f3f4f6; font-weight: 600; }}
    .sev-critical {{ color: #7c3aed; font-weight: bold; }}
    .sev-high {{ color: #dc2626; font-weight: bold; }}
    .sev-medium {{ color: #d97706; }}
    .sev-low {{ color: #059669; }}
    .tag-new {{ background: #dbeafe; color: #1d4ed8; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; }}
    .tag-resolved {{ background: #dcfce7; color: #15803d; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; }}
    .empty {{ color: #9ca3af; font-style: italic; }}
  </style>
</head>
<body>
  <h1>Gitopsy Diff Report</h1>
  <div class="meta">
    <strong>{old_project}</strong> snapshot ({old_generated_at})
    &rarr;
    <strong>{new_project}</strong> snapshot ({new_generated_at})
  </div>

  <div class="card">
    <h2>Health Grade</h2>
    {grade_section}
  </div>

  <div class="card">
    <h2>Security Findings</h2>
    {security_section}
  </div>

  <div class="card">
    <h2>Key Files</h2>
    {files_section}
  </div>

  <div class="card">
    <h2>Recommendations</h2>
    {recs_section}
  </div>
</body>
</html>
"""


def render_diff(diff: dict[str, Any], output_path: str) -> None:
    """Render the diff dict as an HTML report.

    Args:
        diff: Output from :func:`compare`.
        output_path: File path to write the HTML report to.
    """
    # Grade section
    grade_section = _render_grade_section(diff)
    security_section = _render_security_section(diff)
    files_section = _render_files_section(diff)
    recs_section = _render_recs_section(diff)

    html = _DIFF_TEMPLATE.format(
        old_project=diff["old_project"],
        new_project=diff["new_project"],
        old_generated_at=diff["old_generated_at"],
        new_generated_at=diff["new_generated_at"],
        grade_section=grade_section,
        security_section=security_section,
        files_section=files_section,
        recs_section=recs_section,
    )

    Path(output_path).write_text(html, encoding="utf-8")


def _grade_color(grade: str) -> str:
    colors = {"A": "#16a34a", "B": "#65a30d", "C": "#ca8a04", "D": "#ea580c", "F": "#dc2626"}
    return colors.get(grade, "#6b7280")


def _render_grade_section(diff: dict[str, Any]) -> str:
    gc = diff.get("grade_change")
    score_change = diff.get("score_change")

    if not gc:
        return "<p class='empty'>Grade data not available in one or both snapshots.</p>"

    old_g, new_g = gc
    improved = diff.get("grade_improved", False)
    direction_class = "improved" if improved else ("regressed" if old_g != new_g else "unchanged")
    arrow_text = "improved" if improved else ("regressed" if old_g != new_g else "unchanged")

    score_html = ""
    if score_change is not None:
        sign = "+" if score_change > 0 else ""
        cls = "improved" if score_change > 0 else ("regressed" if score_change < 0 else "unchanged")
        score_html = f"<p>Score change: <span class='{cls}'>{sign}{score_change} points</span></p>"

    return f"""
    <div class="grade-row">
      <span class="grade-badge" style="background:{_grade_color(old_g)}22; color:{_grade_color(old_g)}">{old_g}</span>
      <span class="arrow">&rarr;</span>
      <span class="grade-badge" style="background:{_grade_color(new_g)}22; color:{_grade_color(new_g)}">{new_g}</span>
      <span class="{direction_class}">{arrow_text}</span>
    </div>
    {score_html}
    """


def _render_security_section(diff: dict[str, Any]) -> str:
    new_f = diff.get("new_findings", [])
    resolved_f = diff.get("resolved_findings", [])

    if not new_f and not resolved_f:
        return "<p class='empty'>No security finding changes.</p>"

    rows = []
    for f in new_f:
        sev = f["severity"]
        rows.append(
            f"<tr><td><span class='tag-new'>new</span></td>"
            f"<td class='sev-{sev}'>{sev}</td>"
            f"<td>{f['category']}</td>"
            f"<td>{f['file']}</td>"
            f"<td>{f['description']}</td></tr>"
        )
    for f in resolved_f:
        sev = f["severity"]
        rows.append(
            f"<tr><td><span class='tag-resolved'>resolved</span></td>"
            f"<td class='sev-{sev}'>{sev}</td>"
            f"<td>{f['category']}</td>"
            f"<td>{f['file']}</td>"
            f"<td>{f['description']}</td></tr>"
        )

    table = (
        "<table><thead><tr><th>Status</th><th>Severity</th><th>Category</th>"
        "<th>File</th><th>Description</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return table


def _render_files_section(diff: dict[str, Any]) -> str:
    new_f = diff.get("new_files", [])
    deleted_f = diff.get("deleted_files", [])

    if not new_f and not deleted_f:
        return "<p class='empty'>No key file changes.</p>"

    items = []
    for p in new_f:
        items.append(f"<li><span class='tag-new'>new</span> {p}</li>")
    for p in deleted_f:
        items.append(f"<li><span class='tag-resolved'>removed</span> {p}</li>")

    return "<ul>" + "".join(items) + "</ul>"


def _render_recs_section(diff: dict[str, Any]) -> str:
    new_r = diff.get("new_recommendations", [])
    resolved_r = diff.get("resolved_recommendations", [])

    if not new_r and not resolved_r:
        return "<p class='empty'>No recommendation changes.</p>"

    items = []
    for r in new_r:
        items.append(f"<li><span class='tag-new'>new</span> {r}</li>")
    for r in resolved_r:
        items.append(f"<li><span class='tag-resolved'>resolved</span> {r}</li>")

    return "<ul>" + "".join(items) + "</ul>"

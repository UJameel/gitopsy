"""Jinja2-based HTML report renderer."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gitopsy.models.schemas import GitopsyReport
from gitopsy.report.charts import debt_bar_chart, language_doughnut_chart


_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_NAME = "template.html"


def render(report: GitopsyReport, output_path: str) -> None:
    """Render a GitopsyReport to a self-contained HTML file.

    Args:
        report: The full GitopsyReport.
        output_path: Absolute path where the HTML file should be written.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,  # We control the data — no user input in templates
    )
    template = env.get_template(_TEMPLATE_NAME)

    lang_chart_json = language_doughnut_chart(report)
    debt_chart_json = debt_bar_chart(report)

    html = template.render(
        report=report,
        lang_chart_json=lang_chart_json,
        debt_chart_json=debt_chart_json,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

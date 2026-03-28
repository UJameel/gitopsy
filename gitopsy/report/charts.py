"""Chart.js payload generators for tech debt scores and language breakdown."""

from __future__ import annotations

import json

from gitopsy.models.schemas import GitopsyReport


def _grade_color(score: int) -> str:
    """Return a color string based on score (0=green, 100=red)."""
    if score <= 20:
        return "#3fb950"  # green
    if score <= 40:
        return "#8b949e"  # grey-green
    if score <= 60:
        return "#d29922"  # yellow
    if score <= 80:
        return "#f0883e"  # orange
    return "#f85149"  # red


def debt_bar_chart(report: GitopsyReport) -> str:
    """Generate a Chart.js bar chart payload for tech debt dimensions.

    Returns a JSON string suitable for use in Chart.js config.
    """
    if report.tech_debt is None:
        return "{}"

    dims = report.tech_debt.dimensions
    labels = [d.replace("_", " ").title() for d in dims]
    data = [dims[k].score for k in dims]
    colors = [_grade_color(s) for s in data]

    config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Tech Debt Score",
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": colors,
                    "borderWidth": 1,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": "Tech Debt by Dimension (0=clean, 100=critical)",
                    "color": "#c9d1d9",
                },
            },
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "max": 100,
                    "ticks": {"color": "#8b949e"},
                    "grid": {"color": "#30363d"},
                },
                "x": {
                    "ticks": {"color": "#8b949e"},
                    "grid": {"color": "#30363d"},
                },
            },
        },
    }
    return json.dumps(config)


def language_doughnut_chart(report: GitopsyReport) -> str:
    """Generate a Chart.js doughnut chart payload for language breakdown.

    Returns a JSON string suitable for use in Chart.js config.
    """
    if report.architecture is None:
        return "{}"

    breakdown = report.architecture.language_breakdown
    if not breakdown:
        return "{}"

    # Sort by percentage descending, take top 10
    sorted_langs = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [lang for lang, _ in sorted_langs]
    data = [pct for _, pct in sorted_langs]

    palette = [
        "#58a6ff", "#3fb950", "#f85149", "#d29922", "#f0883e",
        "#bc8cff", "#79c0ff", "#56d364", "#ffa657", "#ff7b72",
    ]
    colors = palette[:len(labels)]

    config = {
        "type": "doughnut",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": colors,
                    "hoverOffset": 4,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": "right",
                    "labels": {"color": "#c9d1d9"},
                },
                "title": {
                    "display": True,
                    "text": "Language Breakdown",
                    "color": "#c9d1d9",
                },
            },
        },
    }
    return json.dumps(config)

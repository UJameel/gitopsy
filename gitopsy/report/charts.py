"""Chart.js payload generators for tech debt scores and language breakdown."""

from __future__ import annotations

import json

from gitopsy.models.schemas import GitopsyReport

# Chart color constants — match CSS token values in template.html :root block
CHART_GREEN = '#3fb950'
CHART_GREY = '#8b949e'
CHART_YELLOW = '#d29922'
CHART_ORANGE = '#f0883e'
CHART_RED = '#f85149'
CHART_AXIS = '#8b949e'
CHART_GRID = '#30363d'
CHART_LABEL = '#c9d1d9'
CHART_GREEN_BRIGHT = '#56d364'
CHART_PALETTE = [
    '#58a6ff', CHART_GREEN, CHART_RED,
    CHART_YELLOW, CHART_ORANGE, '#bc8cff',
    '#79c0ff', CHART_GREEN_BRIGHT, '#ffa657',
    '#ff7b72',
]


def _grade_color(score: int) -> str:
    """Return a color string based on score (0=green, 100=red)."""
    if score <= 20:
        return CHART_GREEN
    if score <= 40:
        return CHART_GREY
    if score <= 60:
        return CHART_YELLOW
    if score <= 80:
        return CHART_ORANGE
    return CHART_RED


def _score_color(score: int) -> str:
    """Return color for a 0-100 score where higher is better."""
    if score >= 80:
        return CHART_GREEN
    if score >= 60:
        return CHART_GREY
    if score >= 40:
        return CHART_YELLOW
    if score >= 20:
        return CHART_ORANGE
    return CHART_RED


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
                    "color": CHART_LABEL,
                },
            },
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "max": 100,
                    "ticks": {"color": CHART_AXIS},
                    "grid": {"color": CHART_GRID},
                },
                "x": {
                    "ticks": {"color": CHART_AXIS},
                    "grid": {"color": CHART_GRID},
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

    colors = CHART_PALETTE[:len(labels)]

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
                    "labels": {"color": CHART_LABEL},
                },
                "title": {
                    "display": True,
                    "text": "Language Breakdown",
                    "color": CHART_LABEL,
                },
            },
        },
    }
    return json.dumps(config)


def score_dashboard_data(report: GitopsyReport) -> str:
    """Generate score dashboard mini-scores for all 8 analyzers.

    Returns a JSON string with scores for each analyzer.
    """
    scores: dict[str, dict] = {}

    # Tech debt overall score (inverted: 100=clean → score 100, 0=clean)
    if report.tech_debt:
        debt_score = max(0, 100 - report.tech_debt.overall_score)
        scores["tech_debt"] = {
            "label": "Tech Debt",
            "score": debt_score,
            "grade": report.tech_debt.grade,
            "color": _score_color(debt_score),
        }

    # Architecture score (based on file count — proxy)
    if report.architecture:
        arch_score = 80  # default good score
        scores["architecture"] = {
            "label": "Architecture",
            "score": arch_score,
            "grade": _score_to_grade(arch_score),
            "color": _score_color(arch_score),
        }

    # Dependencies risk score (inverted)
    if report.dependencies:
        dep_score = max(0, 100 - report.dependencies.risk_score)
        scores["dependencies"] = {
            "label": "Dependencies",
            "score": dep_score,
            "grade": _score_to_grade(dep_score),
            "color": _score_color(dep_score),
        }

    # Conventions consistency
    if report.conventions:
        conv_score = report.conventions.consistency_score
        scores["conventions"] = {
            "label": "Conventions",
            "score": conv_score,
            "grade": _score_to_grade(conv_score),
            "color": _score_color(conv_score),
        }

    # API surface score
    if report.api:
        if report.api.total_routes > 0:
            doc_ratio = 1 - (report.api.undocumented_routes / max(report.api.total_routes, 1))
            api_score = int(doc_ratio * 100)
        else:
            api_score = 100
        scores["api"] = {
            "label": "API",
            "score": api_score,
            "grade": _score_to_grade(api_score),
            "color": _score_color(api_score),
        }

    # Security score (inverted from risk)
    if report.security:
        risk_to_score = {"low": 90, "medium": 60, "high": 30, "critical": 0}
        sec_score = risk_to_score.get(report.security.risk_level, 50)
        scores["security"] = {
            "label": "Security",
            "score": sec_score,
            "grade": _score_to_grade(sec_score),
            "color": _score_color(sec_score),
        }

    # Onboarding (proxy: has setup steps)
    if report.onboarding:
        ob_score = 80 if report.onboarding.setup_steps else 50
        scores["onboarding"] = {
            "label": "Onboarding",
            "score": ob_score,
            "grade": _score_to_grade(ob_score),
            "color": _score_color(ob_score),
        }

    # Setup guide (proxy: has prerequisites)
    if report.setup:
        setup_score = 80 if report.setup.prerequisites else 50
        scores["setup"] = {
            "label": "Setup",
            "score": setup_score,
            "grade": _score_to_grade(setup_score),
            "color": _score_color(setup_score),
        }

    # Overall score: average of all present scores
    if scores:
        avg = int(sum(v["score"] for v in scores.values()) / len(scores))
    else:
        avg = 0

    return json.dumps({
        "overall": avg,
        "overall_grade": _score_to_grade(avg),
        "scores": scores,
    })


def _score_to_grade(score: int) -> str:
    """Convert a 0-100 score to letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 65:
        return "C"
    if score >= 50:
        return "D"
    return "F"

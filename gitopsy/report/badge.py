"""SVG badge generation for Gitopsy grades."""

from __future__ import annotations


_COLORS: dict[str, str] = {
    "A": "#44cc11",  # green
    "B": "#97ca00",  # yellow-green
    "C": "#dfb317",  # yellow
    "D": "#fe7d37",  # orange
    "F": "#e05d44",  # red
}


def generate_badge(grade: str, score: int) -> str:
    """Generate a shields.io-style SVG badge showing the Gitopsy grade.

    Args:
        grade: Letter grade (A/B/C/D/F).
        score: Numeric score (0-100).

    Returns:
        SVG string for the badge.
    """
    color = _COLORS.get(grade.upper(), "#9f9f9f")
    label = "gitopsy"
    value = f"{grade} ({score})"

    # Approximate text widths (6px per char + padding)
    label_width = len(label) * 6 + 10
    value_width = len(value) * 6 + 10
    total_width = label_width + value_width

    label_x = label_width // 2
    value_x = label_width + value_width // 2

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="20" role="img" aria-label="{label}: {value}">
    <title>{label}: {value}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{label_width}" height="20" fill="#555"/>
        <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
        <rect width="{total_width}" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="110">
        <text x="{label_x * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(label_width - 10) * 10}" lengthAdjust="spacing">{label}</text>
        <text x="{label_x * 10}" y="140" transform="scale(.1)" textLength="{(label_width - 10) * 10}" lengthAdjust="spacing">{label}</text>
        <text x="{value_x * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(value_width - 10) * 10}" lengthAdjust="spacing">{value}</text>
        <text x="{value_x * 10}" y="140" transform="scale(.1)" textLength="{(value_width - 10) * 10}" lengthAdjust="spacing">{value}</text>
    </g>
</svg>"""
    return svg


def get_badge_color(grade: str) -> str:
    """Return the hex color for a given grade letter."""
    return _COLORS.get(grade.upper(), "#9f9f9f")

"""Tests for badge SVG generation."""

from __future__ import annotations

import pytest

from gitopsy.report.badge import generate_badge, get_badge_color


class TestBadgeGeneratesSVG:
    def test_badge_generates_svg(self):
        svg = generate_badge("A", 95)
        assert svg.strip().startswith("<svg")
        assert "</svg>" in svg

    def test_badge_contains_grade_and_score(self):
        svg = generate_badge("B", 75)
        assert "B" in svg
        assert "75" in svg

    def test_badge_contains_label(self):
        svg = generate_badge("A", 90)
        assert "gitopsy" in svg

    def test_badge_valid_xml_structure(self):
        svg = generate_badge("C", 60)
        assert "xmlns=" in svg
        assert "<rect" in svg
        assert "<text" in svg


class TestBadgeColors:
    def test_badge_color_for_grade_a_is_green(self):
        color = get_badge_color("A")
        assert color == "#44cc11"

    def test_badge_color_for_grade_b_is_yellow_green(self):
        color = get_badge_color("B")
        assert color == "#97ca00"

    def test_badge_color_for_grade_c_is_yellow(self):
        color = get_badge_color("C")
        assert color == "#dfb317"

    def test_badge_color_for_grade_d_is_orange(self):
        color = get_badge_color("D")
        assert color == "#fe7d37"

    def test_badge_color_for_grade_f_is_red(self):
        color = get_badge_color("F")
        assert color == "#e05d44"

    def test_badge_color_for_unknown_grade_is_grey(self):
        color = get_badge_color("Z")
        assert color == "#9f9f9f"

    def test_badge_color_case_insensitive(self):
        assert get_badge_color("a") == get_badge_color("A")
        assert get_badge_color("f") == get_badge_color("F")

    def test_badge_svg_contains_grade_a_color(self):
        svg = generate_badge("A", 95)
        assert "#44cc11" in svg

    def test_badge_svg_contains_grade_f_color(self):
        svg = generate_badge("F", 10)
        assert "#e05d44" in svg

---
phase: 05-theme-toggle-chart-js-visual-polish
plan: 01
subsystem: ui
tags: [chart.js, css, jinja2, glassmorphism, color-mix, fouc-prevention, theme]

# Dependency graph
requires:
  - phase: 04-css-foundation-token-system
    provides: CSS token system with :root dark defaults and [data-theme='light'] overrides
provides:
  - Chart.js 4.4.0 vendor file inlined via Jinja (removes CDN dependency)
  - FOUC prevention script reading localStorage gitopsy-theme before first paint
  - All 23 rgba() tint backgrounds converted to theme-aware color-mix()
  - Sticky glassmorphism header with backdrop-filter blur(12px)
  - Score hero radial gradient glow pseudo-element
  - data-score attribute on .score-overall-badge for JS animation
affects: [05-02, 06-mobile-responsiveness, 07-playwright-validation]

# Tech tracking
tech-stack:
  added: [Chart.js 4.4.0 (vendored at gitopsy/report/vendors/chart.umd.min.js)]
  patterns:
    - color-mix(in srgb, var(--token) 15%, transparent) for theme-aware tint backgrounds
    - FOUC prevention via synchronous inline script in <head> before CSS
    - Chart.js chrome colors owned by JS defaults (not Python config)
    - Vendor file injected via Jinja chartjs_source variable

key-files:
  created:
    - gitopsy/report/vendors/chart.umd.min.js
  modified:
    - gitopsy/report/renderer.py
    - gitopsy/report/charts.py
    - gitopsy/report/template.html

key-decisions:
  - "Chart.js inlined from vendor file (205KB) — removes CDN dependency for offline-first guarantee"
  - "color-mix() replaces all 23 rgba() tint backgrounds — tints now adapt to light/dark theme automatically"
  - "FOUC script reads localStorage gitopsy-theme synchronously in <head> before any paint"
  - "Chart chrome colors (axis, grid, label) removed from Python config dicts — JS theme bridge owns them via Chart.defaults"

patterns-established:
  - "color-mix pattern: color-mix(in srgb, var(--token) 15%, transparent) for semi-transparent tint backgrounds"
  - "FOUC pattern: synchronous inline script in <head> before <style> applies theme attribute before CSS parses"
  - "Vendor injection pattern: _VENDORS_DIR / file read_text -> Jinja variable -> {{ var | safe }}"

requirements-completed: [CHART-01, THEME-01, THEME-03, VIS-02, VIS-04]

# Metrics
duration: 15min
completed: 2026-03-29
---

# Phase 5 Plan 01: Theme Toggle + Chart.js Foundation Summary

**Chart.js 4.4.0 vendored and injected inline, all rgba() tints converted to color-mix(), sticky glassmorphism header, and FOUC-safe theme initialization for offline-first HTML report**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-29T06:00:00Z
- **Completed:** 2026-03-29T06:17:00Z
- **Tasks:** 2
- **Files modified:** 4 (3 Python, 1 HTML)

## Accomplishments

- Downloaded Chart.js 4.4.0 (205KB) to `gitopsy/report/vendors/chart.umd.min.js` and wired it into `renderer.py` as `chartjs_source` Jinja variable, replacing the CDN tag in `template.html`
- Converted all 23 `rgba()` tint backgrounds (pills, risk banners, method badges, status badges, severity badges) to `color-mix(in srgb, var(--token) 15%, transparent)` for automatic light/dark adaptation
- Added synchronous FOUC prevention script in `<head>` that reads `localStorage.getItem('gitopsy-theme')` and applies `data-theme` attribute before CSS parses
- Replaced `.header` CSS with sticky glassmorphism (`position: sticky`, `backdrop-filter: blur(12px)`) with separate `[data-theme='light'] .header` override
- Added `.score-overall::before` radial gradient glow pseudo-element and `data-score` attribute for Plan 02's JS animation
- Removed explicit chrome color fields (`CHART_AXIS`, `CHART_GRID`, `CHART_LABEL`) from `debt_bar_chart()` and `language_doughnut_chart()` Python config dicts — Plan 02 JS theme bridge owns them via `Chart.defaults`

## Task Commits

1. **Task 1: Download Chart.js vendor, update renderer.py, remove chart chrome colors** - `ab7f117` (feat)
2. **Task 2: Add FOUC script, inline Chart.js, color-mix tints, glassmorphism, score glow, data-score** - `b640767` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `gitopsy/report/vendors/chart.umd.min.js` - Chart.js 4.4.0 minified vendor file (205KB)
- `gitopsy/report/renderer.py` - Added `_VENDORS_DIR`, reads vendor file, passes `chartjs_source` to template
- `gitopsy/report/charts.py` - Removed explicit chrome color fields from chart config dicts; module-level constants kept
- `gitopsy/report/template.html` - FOUC script, inline Chart.js, color-mix tints, glassmorphism header, score glow, data-score

## Decisions Made

- Chart.js inlined from vendor file (205KB) — CDN tag removed, satisfies offline-first requirement
- color-mix() replaces all 23 rgba() tint backgrounds — tints now adapt to both themes without extra CSS selectors
- FOUC prevention uses synchronous inline script in `<head>` before style block — blocks first paint until theme is applied
- Chrome colors removed from Python chart dicts — JS theme bridge (Plan 02) will set `Chart.defaults.color` and `Chart.defaults.borderColor` dynamically

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Foundation complete for Plan 02: toggle button, chart theme bridge, score counter animation
- `chartjs_source` Jinja variable available in template for `{{ chartjs_source | safe }}` inline injection
- `data-score` attribute on `.score-overall-badge` ready for JS animation
- `Chart.defaults` chrome color ownership transferred from Python to JS (Plan 02 sets them per theme)
- All 154 existing tests pass

---
*Phase: 05-theme-toggle-chart-js-visual-polish*
*Completed: 2026-03-29*

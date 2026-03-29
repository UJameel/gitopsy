---
phase: 04-css-foundation-token-system
plan: 01
subsystem: ui
tags: [css-custom-properties, design-tokens, theme, light-mode, dark-mode, charts]

# Dependency graph
requires: []
provides:
  - CSS token system with dark (default) and light theme override blocks in template.html
  - --green-bright token (#56d364 dark / #2da44e light) for grade-B color
  - --radius token (6px) replacing all hardcoded border-radius: 6px values
  - Zero hex color leaks in the style block outside token definition blocks
  - Module-level chart color constants in charts.py (CHART_GREEN, CHART_GREY, etc.)
affects:
  - 05-theme-toggle-chartjs-visual-polish
  - 06-mobile-responsiveness
  - 07-playwright-validation-polish

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CSS custom property cascade via :root (dark default) + [data-theme='light'] override block
    - Module-level Python constants for chart colors matching CSS token values

key-files:
  created: []
  modified:
    - gitopsy/report/template.html
    - gitopsy/report/charts.py

key-decisions:
  - ":root block defines dark theme (default); [data-theme='light'] block immediately after overrides color tokens only"
  - "--radius and font stack tokens excluded from light block (not theme-dependent)"
  - "rgba() tint values in lines 355-394 left as-is (not hex notation, out of Phase 4 scope per D-09 guidance)"
  - "CHART_GREEN_BRIGHT constant added in charts.py to match --green-bright CSS token semantically"

patterns-established:
  - "Theme override pattern: [data-theme='light'] block placed immediately after :root before all other CSS rules"
  - "Chart constant pattern: module-level CHART_* constants at top of charts.py before function definitions"

requirements-completed:
  - THEME-05
  - VIS-01
  - VIS-05
  - VIS-06

# Metrics
duration: 2min
completed: 2026-03-28
---

# Phase 04 Plan 01: CSS Foundation + Token System Summary

**CSS token system with dark/light theme blocks, --green-bright and --radius tokens, zero hex leaks in style block, and chart color constants extracted to module level**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T07:02:49Z
- **Completed:** 2026-03-28T07:04:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `--green-bright: #56d364` and `--radius: 6px` tokens to `:root` block
- Added `[data-theme='light']` override block with 13 color tokens (GitHub-light inspired palette)
- Fixed all 3 hex color leaks in template.html: .grade-B rule, score-bar-fill Jinja style, score-num Jinja style
- Replaced all 8 `border-radius: 6px` occurrences with `var(--radius)`
- Extracted 9 module-level constants (CHART_GREEN through CHART_LABEL, CHART_GREEN_BRIGHT) and CHART_PALETTE to charts.py
- All 154 existing tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add light theme block, --green-bright token, --radius token, fix all hex leaks in template.html** - `7d93a02` (feat)
2. **Task 2: Extract hardcoded hex values in charts.py to module-level constants** - `19f0c5e` (feat)

## Files Created/Modified

- `gitopsy/report/template.html` - Added comment headers, extended :root with --green-bright and --radius, added [data-theme='light'] block with 13 tokens, fixed .grade-B, 8x border-radius replacements, 2x Jinja inline style fixes
- `gitopsy/report/charts.py` - Added 10 module-level constants (CHART_GREEN, CHART_GREY, CHART_YELLOW, CHART_ORANGE, CHART_RED, CHART_AXIS, CHART_GRID, CHART_LABEL, CHART_GREEN_BRIGHT, CHART_PALETTE), replaced all hex literals in function bodies

## Decisions Made

- Followed locked decisions D-01 through D-09 exactly as specified in CONTEXT.md
- rgba() tint values (lines 355-394) left out of scope — not hex notation, grep audit passes, D-09 defers rgba concerns to Phase 5
- CHART_GREEN_BRIGHT constant added to charts.py even though not strictly required by D-08 — addresses research pitfall 3 to prevent semantic drift between Python and CSS sides

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 (Theme Toggle + Chart.js + Visual Polish) can now proceed safely
- CSS token layer is complete — all CSS rules reference `var(--)` tokens, zero hardcoded hex in style block
- Light mode is functional via `document.documentElement.setAttribute('data-theme', 'light')` in DevTools — no JS toggle needed until Phase 5
- Phase 5 must address: Chart.js JS defaults on lines 1465-1466 (deferred by D-09), rgba() tint adaptation, FOUC prevention script, theme toggle button

## Self-Check: PASSED

- FOUND: gitopsy/report/template.html
- FOUND: gitopsy/report/charts.py
- FOUND: .planning/phases/04-css-foundation-token-system/04-01-SUMMARY.md
- FOUND commit: 7d93a02 (Task 1)
- FOUND commit: 19f0c5e (Task 2)

---
*Phase: 04-css-foundation-token-system*
*Completed: 2026-03-28*

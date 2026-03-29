# Requirements: Gitopsy

**Defined:** 2026-03-28
**Core Value:** One command gives any developer an instant, beautiful HTML report that explains any unfamiliar codebase — no account, no API key, no cloud.

---

## Milestone v2.0 Requirements — Report UI Overhaul

### Theme System

- [x] **THEME-01**: User sees no flash of wrong theme on page load (FOUC prevention via inline `<head>` script)
- [ ] **THEME-02**: User can toggle between light, dark, and system-default modes via a header button
- [x] **THEME-03**: Report auto-detects and applies the OS color scheme preference on first load
- [ ] **THEME-04**: User's theme preference persists across page reloads (localStorage with file:// graceful fallback)
- [x] **THEME-05**: All theme switching achieved via CSS custom property token system — no inline style overrides

### Visual Design

- [x] **VIS-01**: Report uses a full token-based design system (typography, spacing, color, shadow, radius)
- [x] **VIS-02**: Header is sticky with glassmorphism effect (`backdrop-filter: blur`) in both light and dark themes
- [ ] **VIS-03**: Tech debt / health score animates from 0 to final value on page load (`requestAnimationFrame`)
- [x] **VIS-04**: Score/grade hero section uses gradient accents for visual depth
- [x] **VIS-05**: Light theme palette is WCAG AA compliant (4.5:1 contrast minimum for normal text)
- [x] **VIS-06**: Dark theme uses layered surface depths — not flat black backgrounds

### Mobile Responsiveness

- [ ] **MOBL-01**: Report layout adapts cleanly at 768px breakpoint (tablet)
- [ ] **MOBL-02**: Report layout adapts cleanly at 480px breakpoint (mobile)
- [ ] **MOBL-03**: Tab navigation is horizontally scrollable on mobile with no layout overflow
- [ ] **MOBL-04**: All interactive elements (buttons, tabs, links) have touch targets ≥ 44px
- [ ] **MOBL-05**: Charts scale and remain readable on mobile screen widths

### Chart.js Integration

- [x] **CHART-01**: Chart.js is inlined into the HTML report (removes CDN dependency, enables true offline use)
- [ ] **CHART-02**: All chart chrome colors (axes, grid lines, labels, tooltips) update on theme switch
- [ ] **CHART-03**: Theme switch causes no chart flicker or full re-render (uses `chart.update('none')`)

### Playwright Validation

- [ ] **VAL-01**: Playwright screenshots cover all 4 states: desktop-light, desktop-dark, mobile-light, mobile-dark
- [ ] **VAL-02**: Playwright tests confirm FOUC prevention (no wrong-theme flash on load)
- [ ] **VAL-03**: Visual validation process is documented for future UI iteration

## Deferred Requirements (v3)

### Advanced Visual

- **ADV-01**: Animated transitions between tabs (slide/fade)
- **ADV-02**: Collapsible sections with smooth expand/collapse animation
- **ADV-03**: Syntax highlighting in code snippets within the report

### Accessibility

- **ACC-01**: Full keyboard navigation support
- **ACC-02**: Screen reader ARIA labels on all interactive elements

## Out of Scope (v2.0)

| Feature | Reason |
|---------|--------|
| CSS framework (Tailwind, Bootstrap) | Violates self-contained HTML constraint |
| External Google Fonts | Requires network — must use system fonts or inline |
| JavaScript framework (React, Vue) | Violates self-contained HTML constraint |
| Real-time theme sync across tabs | Over-engineering for a static report |
| Print stylesheet | Out of scope for v2.0 |

## Traceability (v2.0)

| Requirement | Phase | Status |
|-------------|-------|--------|
| THEME-01 | Phase 5 | Complete |
| THEME-02 | Phase 5 | Pending |
| THEME-03 | Phase 5 | Complete |
| THEME-04 | Phase 5 | Pending |
| THEME-05 | Phase 4 | Complete |
| VIS-01 | Phase 4 | Complete |
| VIS-02 | Phase 5 | Complete |
| VIS-03 | Phase 5 | Pending |
| VIS-04 | Phase 5 | Complete |
| VIS-05 | Phase 4 | Complete |
| VIS-06 | Phase 4 | Complete |
| MOBL-01 | Phase 6 | Pending |
| MOBL-02 | Phase 6 | Pending |
| MOBL-03 | Phase 6 | Pending |
| MOBL-04 | Phase 6 | Pending |
| MOBL-05 | Phase 6 | Pending |
| CHART-01 | Phase 5 | Complete |
| CHART-02 | Phase 5 | Pending |
| CHART-03 | Phase 5 | Pending |
| VAL-01 | Phase 7 | Pending |
| VAL-02 | Phase 7 | Pending |
| VAL-03 | Phase 7 | Pending |

**Coverage:**
- v2.0 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---

## v1.0 Requirements (Shipped — All Complete)

### CLI & Package

- [x] **CLI-01**: `gitopsy .` analyzes the current directory and writes `gitopsy-report.html`
- [x] **CLI-02**: `gitopsy /path/to/repo` analyzes any given path
- [x] **CLI-03**: `gitopsy . --output report.html` supports custom output path
- [x] **CLI-04**: `gitopsy . --analyzers arch,debt` runs specific analyzers only
- [x] **CLI-05**: `gitopsy . --json` outputs raw JSON to stdout
- [x] **CLI-06**: Package is installable via `pip install gitopsy`
- [x] **CLI-07**: `python -m gitopsy` entry point works

### Scanners, Analyzers, Report, Skill (v1.0 — Complete)

All CLI, SCAN, ARCH, DEBT, ONBD, DEPS, CONV, API, SEC, SETUP, RPT, SKILL, TEST, DOC, V2-01–V2-05 requirements shipped in Phases 1–3.

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 — v2.0 milestone requirements added; traceability updated with correct phase numbers (4-7)*

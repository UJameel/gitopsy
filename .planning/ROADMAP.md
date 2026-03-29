# Roadmap: Gitopsy

**Created:** 2026-03-28
**Granularity:** Coarse (3 phases per milestone)

## Milestones

- ✓ **v1.0 Core Engine** — Phases 1-3 (shipped 2026-03-28)
- **v2.0 Report UI Overhaul** — Phases 4-7 (in progress)

---

<details>
<summary>v1.0 Core Engine (Phases 1-3) — SHIPPED 2026-03-28</summary>

## Phase Overview (v1.0)

| Phase | Name | Status | Requirements |
|-------|------|--------|--------------|
| 1 | MVP Core | Complete | CLI, scanners, arch/debt/onboarding analyzers, 3-tab report, TDD fixtures |
| 2 | Full Suite | Complete | Deps, conventions, API, security, setup analyzers, full 8-tab report, skill |
| 3 | Polish & Virality | Complete | GitHub Action, badge, comparison, example reports |

---

## Phase 1: MVP Core

**Goal:** Ship a working `gitopsy .` CLI that analyzes any Python or JS repo and produces a beautiful 3-tab HTML report covering Architecture, Tech Debt, and Onboarding. All code written TDD with fixture repos. Tested against real public repos.

**Requirements covered:** CLI-01–07, SCAN-01–04, ARCH-01–08, DEBT-01–09, ONBD-01–08, RPT-01–08, TEST-01–05, DOC-01–02

**Success criteria:**
- `gitopsy .` on the Gitopsy repo itself produces a valid HTML report
- `gitopsy /path/to/flask-repo` produces a valid report on the Flask source
- All Phase 1 tests pass with ≥80% coverage
- HTML report opens in browser with no external deps

**Plans:**

### Plan 1.1: Project scaffold + infrastructure
- `pyproject.toml`, `setup.cfg`, package structure
- `gitopsy/__init__.py`, `__main__.py`, `cli.py` (Click)
- `gitopsy/models/schemas.py` (all Pydantic schemas)
- `gitopsy/scanners/file_tree.py`, `language_detect.py`, `git_history.py`, `pattern_match.py`
- `tests/fixtures/` — flask-app, nextjs-app, python-cli stubs
- Tests written first for all scanner modules

### Plan 1.2: Architecture Analyzer (TDD)
- Tests first: `tests/test_architecture.py`
- `gitopsy/analyzers/architecture.py`
- Framework detection, structure pattern, entry points, dep graph, file ranking

### Plan 1.3: Tech Debt Scorer (TDD)
- Tests first: `tests/test_tech_debt.py`
- `gitopsy/analyzers/tech_debt.py`
- All 7 dimensions, overall score, grade, recommendations

### Plan 1.4: Onboarding Guide Generator (TDD)
- Tests first: `tests/test_onboarding.py`
- `gitopsy/analyzers/onboarding.py`
- README parsing, key files, setup steps, contributors, gotchas

### Plan 1.5: HTML Report + Orchestrator (3 tabs)
- `gitopsy/report/template.html` (inline CSS/JS, Chart.js, dark theme)
- `gitopsy/report/renderer.py` (Jinja2 assembly)
- `gitopsy/report/charts.py` (Chart.js payloads)
- `gitopsy/orchestrator.py` (chains all Phase 1 analyzers)
- Integration test: full pipeline on fixture repos
- Real repo testing: clone Flask, run gitopsy, validate output

### Plan 1.6: CLI polish + docs
- `--analyzers`, `--json`, `--output` flags working
- README with install + usage + screenshot placeholder
- CONTRIBUTING.md
- Package `pip install gitopsy` working locally

---

## Phase 2: Full Suite

**Goal:** Add the remaining 5 analyzers (dependencies, conventions, API extractor, security, setup guide), extend the HTML report to 8 tabs with score dashboard, and ship the Claude Code skill.

**Requirements covered:** DEPS-01–05, CONV-01–08, API-01–05, SEC-01–08, SETUP-01–07, RPT-09–15, SKILL-01–03

**Success criteria:**
- All 8 analyzer tabs render in the HTML report
- Security scanner catches a known hardcoded secret in a test fixture
- API extractor finds all routes in the flask-app fixture
- `/gitopsy` skill works end-to-end in Claude Code

**Plans:**

### Plan 2.1: Dependency Mapper (TDD)
- Tests first: `tests/test_dependencies.py`
- `gitopsy/analyzers/dependencies.py`
- Parse npm/pip/cargo/go/gem manifests, version comparison, license detection

### Plan 2.2: Convention Detector (TDD)
- Tests first: `tests/test_conventions.py`
- `gitopsy/analyzers/conventions.py`
- Naming, formatting, import style, error handling, test patterns

### Plan 2.3: API Extractor (TDD)
- Tests first: `tests/test_api_extractor.py`
- `gitopsy/analyzers/api_extractor.py`
- Express/Flask/FastAPI/Django/Next.js route extraction, CLI commands, exports

### Plan 2.4: Security Surface Scanner (TDD)
- Tests first: `tests/test_security.py`
- `gitopsy/analyzers/security_surface.py`
- Secret detection, env file checks, CORS, SQL injection signals, risk scoring

### Plan 2.5: Setup Guide Builder (TDD)
- Tests first: `tests/test_setup_guide.py`
- `gitopsy/analyzers/setup_guide.py`
- Prerequisites, install steps, env vars, DB setup, run commands, common issues

### Plan 2.6: Full 8-tab report + score dashboard
- Extend `template.html` with all 8 tabs
- Score dashboard (overall health score + per-dimension mini-scores)
- Search/filter on tables, collapsible sections
- Update orchestrator to include all analyzers

### Plan 2.7: Claude Code Skill
- `.claude/skills/gitopsy/SKILL.md`
- End-to-end test: skill runs analyzers via bash, renders HTML

---

## Phase 3: Polish & Virality

**Goal:** Make Gitopsy spreadable — GitHub Action, badge generation, comparison mode, example reports for famous repos.

**Requirements covered:** V2-01–05

**Success criteria:**
- GitHub Action `gitopsy-action` produces a report on any public repo via CI
- Badge SVG embeds in README showing live Gitopsy score
- Example reports for React, Flask, FastAPI included in docs/

**Plans:**

### Plan 3.1: GitHub Action
- `action.yml` + Docker/composite action
- Uploads HTML report as artifact

### Plan 3.2: Badge generation
- `gitopsy . --badge` outputs badge SVG
- Shield.io-compatible JSON endpoint alternative

### Plan 3.3: Comparison mode
- `gitopsy diff report-v1.json report-v2.json`
- Highlights regressions and improvements

### Plan 3.4: Example reports + launch assets
- Run gitopsy on React, Flask, FastAPI repos
- Include outputs in `docs/examples/`
- Demo GIF in README

</details>

---

## v2.0 Report UI Overhaul (Phases 4-7)

**Milestone Goal:** Transform the Gitopsy HTML report into a production-quality dashboard with light/dark mode, mobile responsiveness, and Playwright-validated UI quality — all inlined into a single self-contained HTML file with zero new runtime dependencies.

## Phases

- [x] **Phase 4: CSS Foundation + Token System** — Extract all hardcoded colors into CSS custom properties; define light and dark theme token blocks; establish the prerequisite layer for all v2.0 work (completed 2026-03-29)
- [ ] **Phase 5: Theme Toggle + Chart.js + Visual Polish** — Wire the user-facing theme toggle; inline Chart.js; implement animated score counter; add glassmorphism header and gradient accents
- [ ] **Phase 6: Mobile Responsiveness** — Adapt the report layout to tablet and mobile breakpoints; make tabs horizontally scrollable; ensure touch-friendly targets and readable charts at all screen sizes
- [ ] **Phase 7: Playwright Validation + Polish** — Run four-state Playwright screenshot matrix; verify FOUC prevention; document visual validation workflow for future UI iteration

## Phase Details

### Phase 4: CSS Foundation + Token System
**Goal**: All colors in the report are tokenized into CSS custom properties, with both light and dark theme blocks fully defined — creating the prerequisite layer every other v2.0 phase depends on.
**Depends on**: Phase 3 (v1.0 complete)
**Requirements**: THEME-05, VIS-01, VIS-05, VIS-06
**Success Criteria** (what must be TRUE):
  1. Running `grep -n '#[0-9a-fA-F]\{3,6\}' template.html` returns zero results outside `:root` blocks — no hardcoded colors survive the audit
  2. Manually setting `data-theme="light"` in DevTools renders a fully legible, correctly-colored light-mode report with no broken or missing colors
  3. The light theme palette passes WCAG AA contrast (4.5:1 minimum for normal text) across all text/background pairings
  4. The dark theme uses layered surface depths — at least two visually distinct background levels rather than a flat black background
  5. All color, spacing, typography, shadow, and radius decisions reference named CSS custom property tokens — no inline style color attributes remain
**Plans:** 1/1 plans complete
Plans:
- [x] 04-01-PLAN.md — CSS token system: light theme block, hex leak fixes, radius token, charts.py constant extraction

### Phase 5: Theme Toggle + Chart.js + Visual Polish
**Goal**: Users can toggle between light, dark, and system-default themes with no flash on load; Chart.js is fully inlined; charts update on theme switch without flicker; the header has glassmorphism; the score hero animates on load.
**Depends on**: Phase 4
**Requirements**: THEME-01, THEME-02, THEME-03, THEME-04, VIS-02, VIS-03, VIS-04, CHART-01, CHART-02, CHART-03
**Success Criteria** (what must be TRUE):
  1. Hard-reloading the report with `localStorage.setItem('gitopsy-theme', 'light')` pre-set shows the light theme immediately — no white flash or theme flip visible during load
  2. Clicking the header theme toggle cycles between light, dark, and system-default; the chosen preference survives a page reload including when opened via `file://` protocol
  3. Toggling between light and dark updates all chart axis labels, grid lines, legends, and tooltip backgrounds immediately — with no chart destroy/recreate flicker
  4. The report HTML file loads and renders correctly with no network connection (Chart.js is inlined, no CDN dependency)
  5. The tech debt / health score animates from 0 to its final value on page load; the score hero section displays gradient accents
**Plans:** 1/2 plans executed
Plans:
- [x] 05-01-PLAN.md — Chart.js vendor inlining, FOUC script, color-mix tints, glassmorphism header, score hero glow CSS
- [ ] 05-02-PLAN.md — Theme toggle button + JS, chart theme bridge, score animation

### Phase 6: Mobile Responsiveness
**Goal**: The report layout adapts cleanly at 768px and 480px breakpoints; tab navigation is horizontally scrollable on mobile; all interactive elements meet touch target minimums; charts remain visible and readable at mobile widths.
**Depends on**: Phase 4
**Requirements**: MOBL-01, MOBL-02, MOBL-03, MOBL-04, MOBL-05
**Success Criteria** (what must be TRUE):
  1. At 375px viewport width, no horizontal scroll bar appears and all content fits within the viewport
  2. The tab navigation bar scrolls horizontally on mobile with no tabs wrapping to a second row and no layout overflow
  3. All buttons, tabs, and links have a touch target of at least 44px in height — verifiable by measuring rendered element height in DevTools
  4. Charts are visible with a non-zero rendered height at 375px viewport width — no collapsed or zero-height chart containers
**Plans**: TBD

### Phase 7: Playwright Validation + Polish
**Goal**: Playwright screenshots cover all four states (desktop-light, desktop-dark, mobile-light, mobile-dark); FOUC prevention is verified programmatically; the visual validation process is documented for future UI iteration.
**Depends on**: Phase 5, Phase 6
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. Playwright produces four screenshots covering the full test matrix: desktop-light, desktop-dark, mobile-light, mobile-dark — all four pass without errors
  2. The Playwright FOUC test confirms no wrong-theme flash: the page opens directly in the correct theme state on first paint with no visible flip
  3. A written validation runbook exists documenting how to run the four-state Playwright matrix and interpret results for future UI changes
**Plans**: TBD

## Progress (v2.0)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 4. CSS Foundation + Token System | v2.0 | 1/1 | Complete   | 2026-03-29 |
| 5. Theme Toggle + Chart.js + Visual Polish | v2.0 | 1/2 | In Progress|  |
| 6. Mobile Responsiveness | v2.0 | 0/TBD | Not started | - |
| 7. Playwright Validation + Polish | v2.0 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-03-28*
*v2.0 phases added: 2026-03-28*

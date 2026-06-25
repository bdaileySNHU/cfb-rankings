# EPIC-044: Ticker Redesign — Power Ratings Board

**Status:** 🚧 In Progress
**Priority:** Medium
**Created:** 2026-06-25
**Related:** EPIC-031 (prior UI redesign — superseded look), EPIC-041 (global season selector — intersects Story 44.10)
**Design spec:** `Ticker — Developer Spec` (approved prototype, normative values)

---

## Problem Statement

EPIC-031 gave the app a modern dashboard, but the approved **Ticker** design
moves to a denser, calmer "power ratings board" aesthetic: a dark-default /
cool-white themed single column, a scrolling ticker tape, a 10-column CSS-grid
ratings table with inline heat cells + sparklines, and an in-place team-detail
view — the entire UI driven by **twelve CSS custom properties**.

The spec is normative (exact tokens, type scale, grid geometry, dataviz
formulas). This epic re-skins the product to it without a framework, reusing the
existing FastAPI JSON API and the static vanilla-JS frontend.

---

## Goals

- Implement the spec's 12-token / two-theme system as the single source of truth.
- Rebuild the rankings board + team detail to the spec exactly (§06–§08).
- Keep the existing REST API; add only OFF/DEF per-game scoring.
- Preserve all existing features (predictions, postseason, accuracy, share) —
  re-homed into the new design, not deleted.
- No new runtime dependency; no build step.

---

## Verification note

The static preview (`:4321`) cannot reach the local backend (api.js hardcodes
`:8000`, which is occupied — see local-dev notes). UI is verified by injecting
endpoint-shaped data via the `window.__tkrRender` / `window.__tkrRenderPreds`
hooks in `board.js`; backend changes are verified via FastAPI `TestClient`.

---

## Stories

### Story 44.1: Token foundation & theme system ✅
**Verified** (dark + light, in-browser)
- [x] Define the 12 spec tokens for both themes in `css/tokens.css` (dark default, "Cool white" light)
- [x] Load IBM Plex Sans + Mono (`display=swap`)
- [x] Alias legacy token names (`--bg-primary` → `--bg`, etc.) so other pages reskin by inheritance
- [x] Theme system per §09: `localStorage` key `staturday-theme`, default dark (fixed), sun/moon pill
- [x] `transition: background .35s, color .35s` on root

### Story 44.2: Header bar + ticker tape ✅
**Verified**
- [x] 60px header: brand mark, `WKn · YEAR`, nav, theme pill (shared via `layout.js`)
- [x] 40px ticker tape: 54px LIVE tab + CSS marquee (duplicated track, `translateX(-50%)`, 38s)
- [x] `prefers-reduced-motion: reduce` pauses the tape

### Story 44.3: Ratings board ✅
**Verified**
- [x] One shared `grid-template-columns` for header + rows (§06 track list)
- [x] Identity stripe (team `primary`, fallback `--accent`), ELO in accent
- [x] OFF/DEF heat cells — §07 clamp + per-theme alpha (0.28 dark / 0.18 light), repaint on theme change
- [x] 10-wk sparkline — 70×22 viewBox, non-scaling stroke, trend color
- [x] Δ1W (`deltaDisplay` + `trendColor`), SOS warn only `>0.62`
- [x] Stat ribbon: TOP ELO / FIELD AVG / TOP MOVER (derived client-side)

### Story 44.4: Team detail (in place) 🚧
**Tiles + chart verified; results log unverified against live data**
- [x] Row click → detail in place (no route change); "← BACK TO BOARD"
- [x] Identity card (32px accent ELO + season delta), 5 metric tiles
- [x] Elo history chart — 560×210, pad 14, min−7/max+7, accent area + line + end dot
- [ ] Results log mapped against live `/api/teams/{id}/schedule` (currently defensive/unverified)

### Story 44.5: Backend — OFF/DEF + 10-wk history ✅
**Verified via TestClient**
- [x] `/api/rankings` returns per-team season `off`/`def` PPG (single pass over scored games)
- [x] `RankingEntry` schema declares `off` and `def` (keyword aliased)
- [x] ELO history slice widened 8 → 10 weeks

### Story 44.6: Game predictions card ✅
**Verified**
- [x] Card below the board (hides when a detail opens)
- [x] Columns: MATCHUP (`@`/neutral `v`) · PROJ · split WIN PROB bar · SPREAD · CONF chip
- [x] Win-prob bar split in team brand colors with clash-recolor
- [x] Mapped to the real `/api/predictions` contract

### Story 44.7: Re-home remaining board features 🚧
**Postseason delivered as the projected bracket (Story 44.11). Rest pending.**
- [x] ~~Postseason results~~ → superseded by Story 44.11 (Projected Playoff bracket)
- [ ] Prediction-accuracy banner (planned: ribbon-style tile, no new design)
- [ ] Legend (shrinks to a small key: OFF/DEF heat, sparkline trend, SOS warn)
- [ ] Share Top 25 card (reuse `share.js` canvas; Ticker-styled trigger)
- [ ] Once ported, delete the now-orphaned `js/app.js`

### Story 44.11: Projected playoff bracket ✅
**Verified** (backend via TestClient, UI via injected projection)
- [x] `GET /api/playoff-projection` — CFP-style field (conference-champion auto-bids: 4 power + 1 G5 + at-large), straight Elo seeding, seeds 1–4 bye (`project_playoff_bracket` in `ranking_service.py`)
- [x] Each round simulated with the standard prediction formula (HFA +65 campus / neutral later rounds, scores 30 ± diff/100·3.5)
- [x] 5-column bracket UI in Ticker style: ▸ advances favored side, win-prob bars, `△ HOST` (campus) / bowl-name (neutral) labels, champion "title favorite" card (`board.js`, `board.css`, `index.html`)

### Story 44.8: Resolve detail duplication & reskin other pages ⬜
- [ ] Decide fate of `team.html` (keep vs. redirect to the in-place board detail) and remove duplication
- [ ] Spot-check teams / games / matchup / comparison / simulator / admin / elo-formula in both themes; fix any literal colors or broken layouts (they currently inherit via token aliases only)

### Story 44.9: Team brand metadata completion ⬜
- [ ] Fill `frontend/data/teams-meta.json` for all FBS teams (abbr / mascot / primary / secondary), or
- [ ] Promote to DB columns on `Team` if the data should be editable in-app

### Story 44.10: Polish ⬜
- [ ] Self-host IBM Plex (or `preload`) to drop the render-blocking Google Fonts `@import`
- [ ] Integrate season selector into the Ticker header (closes/aligns with **EPIC-041**); board currently sets `data-season="false"`
- [ ] Accessibility pass: contrast ≥ 4.5:1 both themes, keyboard nav, reduced-motion (partly done)
- [ ] Walk the spec §12 acceptance checklist end-to-end against live data

---

## Acceptance (epic-level)

- [ ] All 12 tokens drive the UI; no literal colors in component CSS except team brand hex
- [ ] Board, detail, and predictions match the spec in both themes
- [ ] No existing feature lost (predictions ✅, postseason / accuracy / share re-homed)
- [ ] `app.js` removed once its features are ported
- [ ] Spec §12 checklist passes against live backend data

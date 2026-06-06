# EPIC-031: UI Redesign — Modern Sports Dashboard

**Status:** ✅ Complete
**Priority:** Medium
**Created:** 2026-05-02
**Related:** EPIC-005 (original frontend), EPIC-018 (UX improvements)

---

## Problem Statement

The current frontend is functional but visually utilitarian. It was built
incrementally across multiple epics using a single 1163-line `style.css` and
plain HTML tables. The design doesn't reflect the quality of the underlying
ELO system and lacks several features that modern sports analytics sites take
for granted:

- **No brand identity** — generic title, no logo, no name beyond "College Football Rankings"
- **No dark mode** — single light theme; sports apps (ESPN, The Athletic, 247Sports) default dark
- **Non-responsive mobile nav** — links overflow on small screens; no hamburger menu
- **No ELO movement indicators** — no ↑/↓ rank change arrows or weekly trend sparklines
- **No team logos** — plain text team names with no visual identity
- **Flat prediction cards** — win % shown as text, no visual probability bar or head-to-head graphic
- **No preseason breakdown** — nowhere to see *why* a team is rated where they are (recruiting + portal + returning + position strength contributions)
- **Static team page** — no ELO history chart, no game-by-game ELO delta visualization
- **Footer says "© 2024"** — stale

### Current Pages
| Page | File | Purpose |
|------|------|---------|
| Rankings | `index.html` | Main top-25 table + predictions |
| All Teams | `teams.html` | Full team list with filters |
| Games | `games.html` | Game results by week |
| Team Detail | `team.html` | Individual team stats |
| Prediction Comparison | `comparison.html` | ELO vs AP poll accuracy |
| How It Works | `elo-formula.html` | Formula explanation |

---

## Goals

1. **Modern sports aesthetic** — dark-first design, strong typography, feels like a real analytics product
2. **Responsive at every breakpoint** — mobile nav, touch-friendly tables, readable on phones
3. **Data visualization** — ELO trend sparklines, probability bars, preseason rating breakdown
4. **Team identity** — team logos via CFBD API (free), color accents per team on detail page
5. **Preseason transparency** — show the components that make up a team's preseason rating
6. **No framework lock-in** — keep vanilla HTML/CSS/JS; no React/Vue build step required on the static server

---

## Stories

### Story 31.1: Design System & Dark Theme ✅
**Priority:** P0
**Effort:** 3–4 hours

Establish the visual foundation everything else builds on. Replace `style.css`
with a new design token system.

**Tasks:**
- [ ] Define CSS custom properties for both light and dark themes:
  - Dark palette: near-black background (`#0f1117`), card surface (`#1a1d27`), muted border (`#2d3148`)
  - Accent: keep gold (`#d69e2e`) — works on dark, feels like a trophy
  - Text hierarchy: primary white, secondary slate, muted gray
  - Semantic colors: win green, loss red, neutral gray
- [ ] Add `prefers-color-scheme: dark` media query (auto) + manual toggle stored in `localStorage`
- [ ] Update typography:
  - Headings: `'Inter'` or `'DM Sans'` (Google Fonts, free) — clean and modern
  - Data: tabular numbers (`font-variant-numeric: tabular-nums`) for aligned ELO values
- [ ] Redesign header: tighter, includes site name "Stat-urday" with a small football icon (SVG inline)
- [ ] Redesign navigation: sticky top bar with logo left, links right; collapses to hamburger on mobile (<768px)
- [ ] Update footer: "© 2026 Stat-urday" with links to How It Works and GitHub

**Acceptance Criteria:**
- [ ] Dark mode works via `prefers-color-scheme` and a manual toggle button
- [ ] Nav collapses to hamburger on mobile
- [ ] All existing pages render without layout breaks in both themes
- [ ] Google Fonts loaded with `display=swap` (no render blocking)

---

### Story 31.2: Rankings Page — ELO Movement & Visual Polish ✅
**Priority:** P0
**Effort:** 3–4 hours

The rankings table is the core of the product. Make it feel alive.

**Tasks:**
- [ ] Add rank change column: compare current week rank vs. previous week from `ranking_history`
  - API already returns data — just needs a `/api/rankings?season=X&week=Y` comparison
  - Display: `▲3` (green), `▼2` (red), `—` (no change), `NEW` (first appearance)
- [ ] Add ELO trend sparkline per row: tiny 8-week SVG line chart inline in the table
  - Pull from existing `ranking_history` data
  - Render as an inline `<svg>` — no chart library needed
- [ ] Redesign rank badge: circular, bold, gold for top 5 / silver for top 10 / white for top 25
- [ ] Conference badge: colored dot + abbreviation (replace text-only badges)
- [ ] Make rows clickable → navigate to `team.html?id=X`
- [ ] Sticky header row when scrolling long tables
- [ ] Mobile: collapse SOS/SOS Rank columns; show rank, team, record, ELO only on small screens

**Acceptance Criteria:**
- [ ] Rank change indicators correct relative to prior week
- [ ] Sparklines render for all teams with ≥2 weeks of history
- [ ] Table is readable on 375px mobile screen
- [ ] Click on any row navigates to team page

---

### Story 31.3: Predictions — Probability Bars & Matchup Cards ✅
**Priority:** P1
**Effort:** 2–3 hours

Replace the current text-only prediction cards with visual matchup cards.

**Tasks:**
- [ ] Redesign prediction card as a head-to-head matchup layout:
  ```
  [Team A Logo]  [Team A]    vs    [Team B]  [Team B Logo]
                 ████████████░░░░░░░░░░
                    68%         32%
               Predicted winner: Team A (-7.2 pts)
  ```
- [ ] Probability bar: CSS gradient split at win% — green left / red right, animates on load
- [ ] Show predicted spread in points (derived from ELO difference)
- [ ] Add home/away indicator (already in game data)
- [ ] Group predictions by conference matchup vs. non-conference
- [ ] "Lock of the Week" badge for the highest-confidence prediction (>80%)

**Acceptance Criteria:**
- [ ] All existing prediction data surfaces in new card design
- [ ] Probability bar animates smoothly on page load
- [ ] Home team indicated visually
- [ ] Cards stack cleanly on mobile

---

### Story 31.4: Team Detail — ELO History Chart & Preseason Breakdown ✅
**Priority:** P1
**Effort:** 4–5 hours

The team page is the richest data view but currently shows a flat stats card.

**Tasks:**
- [ ] Add ELO history chart: SVG line chart showing ELO rating week-by-week for the season
  - X-axis: weeks 0–current; Y-axis: ELO range
  - Annotate notable games (big wins = green dot, big losses = red dot)
  - Tooltip on hover showing opponent, result, ELO delta
  - No external chart library — pure SVG + JS
- [ ] Add preseason rating breakdown card (EPIC-030 data):
  ```
  Preseason Rating: 1,713
  ├─ Base:               1,500
  ├─ Recruiting (#3):     +150
  ├─ Transfer Portal (#8): +75
  ├─ Returning Prod (43%): +10
  ├─ Position Strength:    +42
  └─ Prev Season ELO:     −64  (regression from 1,965)
  ```
- [ ] Add team logo (CFBD API: `https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png` or CFBD logo endpoint)
- [ ] Add season record prominently: `8-4` in large type with W/L streak indicator
- [ ] Game log table: each game with opponent, location (H/A/N), result, ELO before/after, delta

**Acceptance Criteria:**
- [ ] ELO chart renders for any team with season history
- [ ] Preseason breakdown shows all 6 components
- [ ] Team logo loads (gracefully falls back to initials if 404)
- [ ] Game log sortable by week

---

### Story 31.5: All Teams Page — Searchable, Filterable Grid ✅
**Priority:** P2
**Effort:** 2–3 hours

The current All Teams page is a plain table. Make it scannable.

**Tasks:**
- [ ] Switch from table to card grid (3-col desktop, 2-col tablet, 1-col mobile)
- [ ] Each card: logo, team name, conference badge, ELO rating, season record
- [ ] Live search filter (client-side, no API call) by team name
- [ ] Conference filter buttons (All / Power 4 / Group of 5 / FCS)
- [ ] Sort options: ELO (default), Alphabetical, Record

**Acceptance Criteria:**
- [ ] Search filters in real-time as user types
- [ ] Conference filter works correctly
- [ ] Cards link to team detail page

---

### Story 31.6: How It Works — Visual Formula Page ✅
**Priority:** P2
**Effort:** 2–3 hours

The current `elo-formula.html` is a wall of text. Redesign as an interactive explainer.

**Tasks:**
- [ ] Visual formula diagram: boxes and arrows showing how preseason components add up
- [ ] Interactive ELO calculator: slider inputs for two team ratings → shows expected win % and predicted spread
- [ ] Expand the preseason section to explain EPIC-030 regression:
  - "Why does Indiana start at 1,613 instead of 1,550?"
  - Show the regression formula visually
- [ ] Accordion sections for each formula component (not a wall of text)

**Acceptance Criteria:**
- [ ] Interactive calculator works for any two ratings
- [ ] Preseason regression formula explained
- [ ] Page readable on mobile

---

## Technical Approach

### No Build Step
Keep the frontend as vanilla HTML/CSS/JS served from the `frontend/` directory.
No webpack, no React. This keeps the VPS deployment trivial (`git pull` + done).

### Team Logos
CFBD API returns a `logos` array per team. The `api.js` module already fetches
team data — add logo URL caching in `localStorage` (24h TTL) to avoid re-fetching.

Fallback for missing logos: a colored circle with the team's initials, using a
hash of the team name to deterministically pick an accent color.

### SVG Charts
All charts are hand-rolled SVG. The ELO sparklines and the season history chart
need only ~50 lines of JS each. No Chart.js or D3 dependency.

### CSS Architecture
Split the monolithic `style.css` into:
```
frontend/css/
  tokens.css        ← design tokens (colors, spacing, type)
  base.css          ← reset, body, typography
  layout.css        ← header, nav, container, footer
  components.css    ← cards, badges, tables, buttons
  pages/
    rankings.css
    team.css
    predictions.css
```

---

## Success Metrics

- [ ] Lighthouse mobile score ≥ 85 (currently untested)
- [ ] Dark mode available and default
- [ ] Rank change indicators live on rankings page
- [ ] ELO history chart live on team pages
- [ ] Preseason breakdown visible on team pages
- [ ] All pages render without horizontal scroll on 375px mobile

---

## Future Enhancements (Post-31)

- **Animated rank movement** — teams visually slide up/down the table on week update
- **Head-to-head comparison page** — two team ELO histories overlaid
- **Radar chart** — position group strength visualization per team (ties into EPIC-030 position data)
- **Notifications** — browser push for upset alerts when a big prediction misses
- **Share card** — generate a shareable image of the top 25 for social media

---

**Epic Owner:** Bryan Dailey
**Related:** EPIC-005 (original frontend), EPIC-018 (UX improvements), EPIC-030 (preseason data to visualize)

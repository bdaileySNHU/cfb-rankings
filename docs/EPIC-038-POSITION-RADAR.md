# EPIC-038: Radar Chart — Position Group Strength

**Status:** ✅ Complete
**Priority:** Medium
**Created:** 2026-05-04 (backlog)
**Completed:** 2026-06-06
**Related:** EPIC-030 (position weights data), EPIC-031 Story 31.4 (team detail page)

---

## Problem Statement

The team detail page surfaces overall ratings (ELO, preseason, SOS) and a
preseason rating breakdown, but nothing visualizes *where* a team's roster
quality concentrates. A radar/spider chart over the nine position groups gives
an at-a-glance read on a team's strengths and weaknesses by position.

---

## Key Discovery

The backend was **already complete**. The endpoint
`GET /api/teams/{team_id}/position-strength` (built during the Preseason
Enhancement Epic, Story 1.5) returns exactly the data a radar needs:

```json
{
  "team_id": 34,
  "team_name": "Georgia",
  "enabled": true,
  "position_scores": { "QB": 92, "RB": 78, "WR": 85, "TE": 70,
                       "OL": 95, "DL": 90, "LB": 82, "DB": 88, "ST": 60 },
  "position_bonus": 124.5,
  "max_bonus": 150,
  "weights": { ... },
  "recruiting_year": 2025
}
```

Scores are 0–100 per group (`src/core/position_service.py::get_position_group_scores`).
The endpoint already handles the no-data case (returns all-zero scores with a
`message` and `recruiting_year: null`). So EPIC-038 reduced to a **frontend-only**
task — no new stories on the backend, no dependency on EPIC-030 being completed.

---

## Implementation

Pure inline SVG, no chart library (consistent with the ELO history chart from
EPIC-031). All colors use CSS theme tokens, so it adapts to light/dark mode.

**Files changed:**

- `frontend/team.html` — new "Position Group Strength" card inserted between the
  Preseason Rating Breakdown and ELO History cards (`#position-radar-card`).
- `frontend/js/team.js`:
  - `POSITION_RADAR_AXES` — the nine groups in display order (QB, RB, WR, TE, OL,
    DL, LB, DB, ST), offense → defense → special teams, clockwise from top.
  - `loadPositionRadar(teamId)` — fetches `/api/teams/{id}/position-strength`,
    falls back to an "unavailable" message on error.
  - `renderPositionRadar(data)` — draws the radar: 4 concentric grid rings
    (25/50/75/100), axis spokes with per-group labels + scores, a filled data
    polygon with vertex dots (each with a `<title>` tooltip), the recruiting-year
    tag in the card header, and a "Roster quality bonus: +N / max" caption.
  - Wired into `loadTeamDetails()` alongside the other team-detail loaders.

### Behavior

- **With data:** full nine-axis radar, accent-filled polygon, bonus caption,
  `"<year> class"` header tag.
- **No data** (e.g. team with no rated players, or before 2026 recruiting data
  publishes — see EPIC-033 Story 33.2): SVG is omitted and the card shows
  "No player data available for this team yet."

---

## Verification

Verified via the static frontend preview (`Frontend (preview)` launch config,
port 4321):

- `renderPositionRadar` produces 5 polygons (4 rings + 1 data), 9 vertex dots,
  18 label/score `<text>` nodes, the bonus caption, and the year tag.
- No-data path renders the message, hides the SVG, and clears the year tag.
- No JS errors originate from the radar code (only the expected backend-404s
  because the local API/DB has no player data).

Note: the local SQLite DB has **0 players**, so the radar shows the no-data
state locally. Production (VPS) carries prior-year recruiting data and renders
the full chart; 2026 data populates once CFBD publishes it (EPIC-033 Story 33.2).

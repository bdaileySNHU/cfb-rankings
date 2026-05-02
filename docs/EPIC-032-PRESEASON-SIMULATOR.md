# EPIC-032: Interactive Preseason Rating Simulator

**Status:** 📋 To Do
**Priority:** High
**Created:** 2026-05-02
**Related:** EPIC-031 (Story 31.6 home for this tool), EPIC-030 (regression params being tuned)

---

## Problem Statement

The preseason formula has six components (base, recruiting, transfer portal,
returning production, position strength, previous season regression) and three
tunable parameters (`previous_season_weight`, `mean_regression_factor`,
`returning_regression_scale`). Right now there is no way to:

- See what each component contributed to a specific team's preseason rating
- Ask "what if Alabama's recruiting was worth less?" and see the ranking impact
- Validate EPIC-030 regression parameters against intuition without editing JSON
  and re-running scripts

The simulator solves all three. It is also the most compelling public-facing
demonstration of how the ELO system works — far better than a static formula
page.

---

## Proposed Solution

### Architecture: Client-Side Simulation

The key design decision is **where** to compute the rankings when weights change.

**Option A — Server-side**: POST custom weights → API recalculates → returns rankings.
  - Pro: always authoritative. Con: 200ms+ round-trip per slider move; laggy.

**Option B — Client-side**: API returns raw component scores once → browser
  recalculates rankings on every slider move.
  - Pro: instant, no server load. Con: formula logic duplicated in JS.

**→ Option B.** The preseason formula is simple arithmetic — it fits in ~30 lines
of JS. The API exposes component scores per team once on page load; everything
after that is local.

### New API Endpoint: `/api/preseason/components`

Returns each team's raw preseason component scores and enough metadata to
recalculate any blended rating client-side.

```json
GET /api/preseason/components?season=2026

[
  {
    "team_id": 12,
    "team_name": "Indiana",
    "conference": "Big Ten",
    "is_fcs": false,
    "base": 1500,
    "recruiting_bonus": 50,
    "transfer_bonus": 0,
    "returning_bonus": 0,
    "position_strength_bonus": 12.3,
    "prev_season_elo": 2014.78,
    "returning_production": 0.251,
    "current_rating": 1613.8,
    "current_rank": 8
  },
  ...
]
```

### Client-Side Simulation Formula

```js
function simulate(team, weights) {
  const base_formula = team.base
    + team.recruiting_bonus   * weights.recruiting_scale
    + team.transfer_bonus     * weights.transfer_scale
    + team.returning_bonus    * weights.returning_scale
    + team.position_strength_bonus * weights.position_scale;

  if (weights.prev_season_weight > 0 && team.prev_season_elo) {
    const dynamic_reg = weights.mean_regression
      + (team.returning_production - 0.5) * weights.returning_regression_scale;
    const regression = Math.max(0.30, Math.min(0.85, dynamic_reg));
    const prev_regressed = 1500 + (team.prev_season_elo - 1500) * regression;
    return (prev_regressed * weights.prev_season_weight)
         + (base_formula  * (1 - weights.prev_season_weight));
  }
  return base_formula;
}
```

### Simulator UI

```
┌─────────────────────────────────────────────────────────┐
│  Preseason Rating Simulator                              │
│                                                          │
│  Recruiting Weight    ████████░░  1.0x  [reset]          │
│  Transfer Portal      ████░░░░░░  0.5x                   │
│  Returning Production ██████░░░░  0.7x                   │
│  Position Strength    ████████░░  1.0x                   │
│  ─────────────────────────────────────────────────────   │
│  Prev Season Weight   ██████░░░░  0.35  ← EPIC-030       │
│  Mean Regression      ███████░░░  0.60                   │
│  Returning Reg Scale  ███████░░░  0.60                   │
│                                          [Reset All]     │
├─────────────────────────────────────────────────────────┤
│  Rank  Team              Rating   Δ Official   Components│
│   1    Georgia           1,792    +17      ▶ breakdown   │
│   2    Ohio State        1,764    −3       ▶ breakdown   │
│   3    Indiana           1,641    +5       ▶ breakdown   │
│  ...                                                     │
└─────────────────────────────────────────────────────────┘
```

- **Sliders update the table instantly** (no network call)
- **Δ Official** column shows how far each team moved from the official rating
- **▶ breakdown** expands a row to show each component's contribution
- **"Reset All"** restores official parameter values
- **"Save as Official"** button (admin only) writes values back to `position_weights.json`
  via a new `PUT /api/admin/preseason-weights` endpoint

---

## Stories

### Story 32.1: `/api/preseason/components` Endpoint
**Priority:** P0
**Effort:** 2–3 hours

**Tasks:**
- [ ] Add `get_preseason_components(season)` method to `RankingService`:
  - For each FBS team, compute all bonus components individually (not just the total)
  - Return a list of component dicts: `{team_id, team_name, conference, is_fcs, base,
    recruiting_bonus, transfer_bonus, returning_bonus, position_strength_bonus,
    prev_season_elo, returning_production, current_rating, current_rank}`
  - Reuse existing bonus-calculation logic from `calculate_preseason_rating` —
    extract into private helpers so both the endpoint and the simulator can call them
- [ ] Add `GET /api/preseason/components` endpoint to `main.py`
  - Query param: `season` (defaults to active season)
  - Response: list of component objects (no auth required — read-only)
- [ ] Add Pydantic schema `PreseasonComponent` to `schemas.py`
- [ ] Add unit tests for `get_preseason_components()`

**Implementation sketch:**

```python
# In RankingService
def _calculate_preseason_bonuses(self, team: Team) -> dict:
    """Return each bonus component individually (used by simulator endpoint)."""
    # Extract the bonus calculation logic currently inside calculate_preseason_rating
    ...
    return {
        "base": base,
        "recruiting_bonus": recruiting_bonus,
        "transfer_bonus": transfer_bonus,
        "returning_bonus": returning_bonus,
        "position_strength_bonus": position_strength_bonus,
    }

def get_preseason_components(self, season: int) -> list[dict]:
    teams = self.db.query(Team).filter(Team.is_fcs == False).all()
    result = []
    for team in teams:
        bonuses = self._calculate_preseason_bonuses(team)
        prev_elo = self._get_previous_season_elo(team.id, season)
        result.append({
            "team_id": team.id,
            "team_name": team.name,
            "conference": team.conference.value if team.conference else None,
            "base": bonuses["base"],
            "recruiting_bonus": bonuses["recruiting_bonus"],
            "transfer_bonus": bonuses["transfer_bonus"],
            "returning_bonus": bonuses["returning_bonus"],
            "position_strength_bonus": bonuses["position_strength_bonus"],
            "prev_season_elo": prev_elo,
            "returning_production": team.returning_production,
            "current_rating": team.elo_rating,
        })
    return result
```

**Acceptance Criteria:**
- [ ] `GET /api/preseason/components?season=2026` returns data for all ~136 FBS teams
- [ ] Component values sum correctly: `base + recruiting + transfer + returning + position ≈ initial_rating` (within rounding when `prev_season_weight=0`)
- [ ] `prev_season_elo` matches week=20 (or highest week) in `ranking_history` for 2025
- [ ] Unit tests pass

---

### Story 32.2: Simulator Frontend Page
**Priority:** P0
**Effort:** 4–5 hours

**Tasks:**
- [ ] Create `frontend/simulator.html` with the layout described above
- [ ] Create `frontend/js/simulator.js`:
  - On load: fetch `/api/preseason/components?season=2026`, cache response
  - Also fetch `/api/admin/config` to seed sliders with current official parameter values
  - Build slider panel with 7 sliders (see parameters below)
  - On any slider change: run `simulate()` for all teams → sort by rating → re-render table
  - Debounce slider input at 16ms (one animation frame) for smooth performance
  - Rank change (Δ Official) column: positive = green, negative = red
  - Expandable breakdown row: shows each component's weighted contribution as a mini bar chart
- [ ] Add "Simulator" link to nav in all HTML pages
- [ ] Sliders and ranges:

| Slider | Min | Max | Step | Default | Meaning |
|--------|-----|-----|------|---------|---------|
| Recruiting Scale | 0.0 | 2.0 | 0.1 | 1.0 | Multiplier on recruiting_bonus |
| Transfer Portal Scale | 0.0 | 2.0 | 0.1 | 1.0 | Multiplier on transfer_bonus |
| Returning Prod Scale | 0.0 | 2.0 | 0.1 | 1.0 | Multiplier on returning_bonus |
| Position Strength Scale | 0.0 | 2.0 | 0.1 | 1.0 | Multiplier on position_bonus |
| Prev Season Weight | 0.0 | 0.7 | 0.05 | 0.35 | EPIC-030 blend weight |
| Mean Regression | 0.30 | 0.85 | 0.05 | 0.60 | Base regression factor |
| Returning Reg Scale | 0.0 | 1.0 | 0.05 | 0.60 | Returning production regression mod |

**Acceptance Criteria:**
- [ ] Sliders update rankings table with no visible lag (< 16ms render)
- [ ] Δ Official column correct relative to `current_rating` from API
- [ ] Row expansion shows per-component breakdown
- [ ] Reset All restores official parameter values
- [ ] Works on mobile (vertical slider stack, scrollable table)

---

### Story 32.3: "Save as Official" Admin Flow
**Priority:** P2
**Effort:** 1–2 hours

Lets the admin lock in a tuned parameter set directly from the simulator UI,
replacing the manual JSON edit workflow from EPIC-030.

**Tasks:**
- [ ] Add `PUT /api/admin/preseason-weights` endpoint:
  - Accepts: `{previous_season_weight, mean_regression_factor, returning_regression_scale}`
  - Writes values back to `src/core/position_weights.json`
  - Requires admin auth (same pattern as existing `/api/admin/*` endpoints)
- [ ] Add "Save as Official" button to simulator page:
  - Only visible when current slider values differ from official values
  - Sends PUT request with current EPIC-030 slider values
  - On success: shows confirmation toast + updates the "official" baseline for Δ column
  - Does NOT automatically reinitialize preseason ratings (that's a separate step)
- [ ] Show warning banner: "Saving changes does not recalculate preseason ratings.
  Run the preseason init script to apply."

**Acceptance Criteria:**
- [ ] PUT endpoint writes correct values to `position_weights.json`
- [ ] Button only appears when values differ from current config
- [ ] Confirmation and warning shown on save

---

### Story 32.4: Tests
**Priority:** P1
**Effort:** 1–2 hours

**Tasks:**
- [ ] Unit tests for `_calculate_preseason_bonuses()`:
  - Recruiting rank 1 → 200, rank 50 → 25, rank 999 → 0
  - Transfer portal rank 5 → 100, rank 999 → 0
  - Returning production 0.85 → 40, 0.25 → 0
- [ ] Unit tests for `get_preseason_components()`:
  - Returns correct component values for a known team
  - `prev_season_elo` pulls from ranking_history correctly
  - FCS teams excluded from results
- [ ] Integration test for `GET /api/preseason/components`:
  - Returns 200 with a list
  - Each item contains all required fields
- [ ] All existing tests continue to pass

---

## Technical Notes

### Refactoring `calculate_preseason_rating`

Currently `calculate_preseason_rating()` computes bonuses inline and returns
only the total. Story 32.1 extracts them into `_calculate_preseason_bonuses()`
which returns a dict. `calculate_preseason_rating()` then calls that helper
and sums the values. This keeps the existing behavior identical while making
components accessible to the new endpoint.

### Why Scale Multipliers (not Absolute Weights)

The sliders use *multipliers* on existing bonuses (1.0x = current behavior)
rather than replacing the bonus tier system entirely. This means:

- The existing bonus tiers (rank 1→5 = 200pts, rank 6→10 = 150pts, etc.) are preserved
- A 2.0x recruiting scale doubles every tier proportionally
- Reset to 1.0x always returns to the current official formula

An alternative would be to expose the raw bonus tier values as sliders (8+
sliders for recruiting alone). That's more powerful but overwhelming. Start
simple — can be extended post-launch.

### Performance

136 FBS teams × 7 weight parameters = trivial client-side math. A full
re-sort and table re-render should complete in < 5ms on any modern device.
No virtualization or lazy rendering needed.

---

## Success Metrics

- [ ] `/api/preseason/components` live in production
- [ ] Simulator page accessible at `/simulator.html`
- [ ] Sliders update rankings with no perceptible lag
- [ ] Indiana's 2026 preseason rating visually explainable using the breakdown row
- [ ] "Save as Official" replaces the manual `position_weights.json` edit workflow

---

## Integration with EPIC-031

When the UI redesign ships, Story 31.6 ("How It Works" page) absorbs and
reskins the simulator using the new design system. The simulator JS logic
(`simulator.js`) remains unchanged — only the HTML/CSS shell updates.

---

**Epic Owner:** Bryan Dailey
**Related:** EPIC-030 (params being tuned), EPIC-031 (visual home for this tool)

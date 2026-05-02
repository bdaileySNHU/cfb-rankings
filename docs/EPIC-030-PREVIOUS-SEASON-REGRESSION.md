# EPIC-030: Previous Season Performance Factor in Preseason Ratings

**Status:** 📋 To Do
**Priority:** High
**Created:** 2026-05-01
**Related:** EPIC-029 (exposed the gap), EPIC-PRESEASON-2026-01 (base formula)

---

## Problem Statement

The current preseason formula resets every team to a base of 1500 and adds bonuses
for recruiting, transfer portal, and returning production. It has **no memory of
previous season performance**, which produces nonsensical results for teams that
significantly outperformed or underperformed their recruiting profile.

### Concrete Example (2026 Preseason)

Indiana finished 2025 at 12-0 with an ELO of **1910.7** — one of the best seasons
in program history. Their 2026 preseason rating came out as **1550** (ranked outside
the top 25) because:

- Recruiting rank: 47 → modest bonus
- Transfer portal rank: 52 → no bonus
- Returning production: 25.1% → no bonus
- Position strength: no player data → no bonus
- Previous season performance: **not considered at all**

Meanwhile Alabama, Georgia, and Ohio State — teams Indiana beat or outpaced all
season — start 2026 at 1700+ purely on recruiting pedigree.

### Root Cause

College football success is driven by coaching, scheme, and player development in
addition to recruiting. A team that goes 12-0 has proven quality that should carry
forward into the next season's starting point, moderated by expected turnover.

This is how virtually all production ELO systems (FiveThirtyEight NFL, 538 NBA, etc.)
handle season transitions: **partial mean regression** rather than full reset.

---

## Proposed Solution

### Design Refinements

**1. Use Postseason (True Final) ELO, Not Mid-Season Snapshot**

`ranking_history` is populated by `save_weekly_rankings()`, which is called each week
during the season. If this was never called for postseason weeks (bowl games, CFP),
the highest entry in `ranking_history` may be week 16–20, missing the full playoff run.

Example: Indiana's local `ranking_history` tops out at **1910.72** (week 20), but the
VPS — where all postseason games were processed — shows **2014.78** after the CFP final.
A query against `ranking_history` alone would silently undercount Indiana's true final ELO.

**Fix:** Before reinitializing preseason ratings for year N, save a final-season snapshot
to `ranking_history` using the live `teams.elo_rating` value (which reflects all processed
games). This guarantees the postseason ELO is captured before it gets overwritten.

**2. Dynamic Regression Based on Returning Production**

Instead of a fixed `mean_regression_factor`, modulate it with the team's
`returning_production` percentage:

- **High returning production** (e.g., 58.9% Texas Tech) → less regression → more
  previous ELO carries forward (same team, same scheme)
- **Low returning production** (e.g., 25.1% Indiana) → more regression → previous
  ELO pulled harder toward 1500 (major roster turnover)

```
dynamic_regression = base_regression + (returning_production - 0.5) * adjustment_scale
dynamic_regression = clamp(dynamic_regression, 0.30, 0.85)
```

With `base_regression=0.60` and `adjustment_scale=0.60`:

| Team        | returning | dynamic_regression |
|-------------|-----------|-------------------|
| Texas Tech  | 0.589     | 0.653             |
| Alabama     | 0.433     | 0.560             |
| Ohio State  | 0.308     | 0.485             |
| Indiana     | 0.251     | 0.451             |

Indiana's regression increases (more turnover → more mean reversion), which is exactly
right — they lost most of their CFP roster. Their strong ELO still provides a meaningful
boost, just appropriately discounted.

### Formula

Add a configurable previous-season blend to `calculate_preseason_rating()`:

```
# Step 0: Ensure final season ELO is saved before preseason init
#   (run once per season transition, before any initialize_team_rating calls)
save_final_season_snapshot(season=prev_season)  # saves teams.elo_rating → ranking_history

# Step 1: Calculate base preseason formula (existing)
base_formula = base + recruiting + transfer + returning + position_strength

# Step 2: Get team's true final ELO from previous season
prev_elo = ranking_history[team][prev_season][max_week].elo_rating
#   (max_week now includes postseason because of Step 0)

# Step 3: Apply dynamic mean regression
#   base_regression pulled toward 1500 more/less based on returning production
dynamic_regression = base_regression + (returning_production - 0.5) * adjustment_scale
dynamic_regression = clamp(dynamic_regression, 0.30, 0.85)
prev_regressed = 1500 + (prev_elo - 1500) * dynamic_regression

# Step 4: Blend
preseason_rating = (prev_regressed * prev_season_weight)
                 + (base_formula   * (1 - prev_season_weight))
```

### Configuration Parameters (added to position_weights.json)

```json
{
  "previous_season_weight": 0.35,
  "_comment_psw": "How much previous season ELO influences preseason (0=ignore, 1=only prev season)",
  "mean_regression_factor": 0.60,
  "_comment_mrf": "Base regression toward 1500 before blending (0=full reset, 1=no regression)",
  "returning_regression_scale": 0.60,
  "_comment_rrs": "How much returning_production modulates regression. 0=fixed regression. Higher values give more weight to continuity signal."
}
```

### Example: Indiana 2026 Preseason with full formula

```
base_formula       = 1550.0   (recruiting/portal/returning/position)
prev_elo           = 2014.78  (Indiana's TRUE final 2025 ELO, postseason included)
returning_prod     = 0.251    (25.1% returning — high turnover)

dynamic_regression = 0.60 + (0.251 - 0.5) * 0.60 = 0.451
prev_regressed     = 1500 + (2014.78 - 1500) * 0.451 = 1732.2

preseason          = (1732.2 * 0.35) + (1550.0 * 0.65)
                   = 606.3 + 1007.5 = 1613.8  ← Top 10, much more reasonable
```

Compare to mid-season ELO (1910.72) with fixed regression (0.60):
```
prev_regressed = 1500 + (1910.72 - 1500) * 0.60 = 1746.4
preseason      = (1746.4 * 0.35) + (1550.0 * 0.65) = 1618.7
```

Both produce top-10 results, but the postseason + dynamic version is more principled:
it uses the true final rating and correctly penalizes high turnover.

### Graceful Degradation

- If no previous season data exists (new team, first season): use base formula only
- If `returning_production` not available: fall back to fixed `mean_regression_factor`
- Weight of 0.0 = identical behavior to current formula (safe default)
- Feature starts disabled until validated

---

## Stories

### Story 30.1: Implement Previous Season Regression in Ranking Service
**Priority:** P0
**Effort:** 2–3 hours

**Tasks:**
- [ ] Add `save_final_season_snapshot(season)` to `RankingService`
  - Reads current `teams.elo_rating` for all teams and writes a final-week entry to
    `ranking_history` (week = `season.current_week + 1` or a sentinel like 99)
  - **Must be called before** any `initialize_team_rating` calls for the next season,
    otherwise the postseason ELO is overwritten and lost
  - Add a utility script `utilities/save_final_season_snapshot.py` that calls this
- [ ] Add `_get_previous_season_elo(team_id, season)` helper to `RankingService`
  - Queries `ranking_history` for the team's highest-week entry in `season-1`
  - Returns `None` if no data exists
- [ ] Add `previous_season_weight`, `mean_regression_factor`, and
  `returning_regression_scale` to `position_weights.json`
  - Default `previous_season_weight` to `0.0` initially (no change to current behavior)
  - Default `mean_regression_factor` to `0.60`
  - Default `returning_regression_scale` to `0.60`
- [ ] Modify `calculate_preseason_rating(team, season=None)` to:
  - Accept optional `season` parameter (falls back to active season if None)
  - Call `_get_previous_season_elo()` when `previous_season_weight > 0`
  - Apply dynamic regression based on `returning_production` when available
  - Apply blend formula
  - Log the previous season contribution at DEBUG level
- [ ] Update `initialize_team_rating(team, season=None)` to pass season through

**Implementation sketch:**

```python
def save_final_season_snapshot(self, season: int) -> int:
    """
    Capture the true postseason-final ELO for all teams into ranking_history.
    Call this BEFORE initializing preseason ratings for the next season.
    Uses a high sentinel week (999) so it always appears as the 'last' entry.
    Returns count of rows saved.
    """
    from src.models.models import RankingHistory, Team
    teams = self.db.query(Team).all()
    count = 0
    for team in teams:
        # Overwrite any existing sentinel entry for this season
        existing = (
            self.db.query(RankingHistory)
            .filter(RankingHistory.team_id == team.id,
                    RankingHistory.season == season,
                    RankingHistory.week == 999)
            .first()
        )
        if existing:
            existing.elo_rating = team.elo_rating
        else:
            self.db.add(RankingHistory(
                team_id=team.id,
                season=season,
                week=999,
                elo_rating=team.elo_rating,
            ))
        count += 1
    self.db.commit()
    logger.info(f"Saved final season snapshot for {season}: {count} teams at sentinel week 999")
    return count


def _get_previous_season_elo(self, team_id: int, current_season: int) -> Optional[float]:
    """Get team's final ELO from the previous season via ranking_history.
    Prefers the sentinel week=999 snapshot (postseason-complete) if available,
    otherwise falls back to the highest recorded week.
    """
    prev_season = current_season - 1
    record = (
        self.db.query(RankingHistory)
        .filter(
            RankingHistory.team_id == team_id,
            RankingHistory.season == prev_season,
        )
        .order_by(RankingHistory.week.desc())
        .first()
    )
    return record.elo_rating if record else None


def calculate_preseason_rating(self, team: Team, season: int = None) -> float:
    # ... existing formula unchanged ...
    base_formula_rating = base + recruiting_bonus + transfer_bonus + returning_bonus + position_bonus

    # Previous season regression (EPIC-030)
    try:
        config = load_position_weights()
        prev_weight = config.get("previous_season_weight", 0.0)
        base_regression = config.get("mean_regression_factor", 0.60)
        returning_scale = config.get("returning_regression_scale", 0.60)

        if prev_weight > 0 and season:
            prev_elo = self._get_previous_season_elo(team.id, season)
            if prev_elo:
                # Dynamic regression: high returning → less regression (team continuity)
                returning_prod = getattr(team, "returning_production", None)
                if returning_prod is not None:
                    dynamic_regression = base_regression + (returning_prod - 0.5) * returning_scale
                    regression = max(0.30, min(0.85, dynamic_regression))
                else:
                    regression = base_regression

                prev_regressed = 1500 + (prev_elo - 1500) * regression
                blended = (prev_regressed * prev_weight) + (base_formula_rating * (1 - prev_weight))
                logger.debug(
                    f"{team.name}: prev_elo={prev_elo:.1f} returning={returning_prod} "
                    f"regression={regression:.3f} → regressed={prev_regressed:.1f} "
                    f"→ blended={blended:.1f} (weight={prev_weight})"
                )
                return blended
    except Exception as e:
        logger.warning(f"Previous season regression failed for {team.name}: {e}")

    return base_formula_rating
```

**Acceptance Criteria:**
- [ ] `save_final_season_snapshot()` writes week=999 entries to `ranking_history` for all teams
- [ ] `_get_previous_season_elo()` returns the week=999 (postseason) ELO when available
- [ ] Returns base formula unchanged when `previous_season_weight = 0.0`
- [ ] Dynamic regression applied when `returning_production` is available
- [ ] Falls back to fixed `mean_regression_factor` when `returning_production` is None
- [ ] Logs previous season contribution at DEBUG level
- [ ] Gracefully returns base formula if previous season data missing or error

---

### Story 30.2: Save Final Season Snapshot and Reinitialize 2026 Preseason
**Priority:** P0  ← must happen before Story 30.3 validation
**Effort:** 30 minutes

**Background:** 2026 preseason was already initialized on the VPS, overwriting
`teams.elo_rating` with preseason values. The 2025 postseason ELO (e.g., Indiana at
2014.78) is still live in `teams.elo_rating` on the VPS **only if** the table was never
updated after the final CFP game. We must check and capture it before proceeding.

**Tasks:**
- [ ] On the VPS, verify Indiana's current `elo_rating` in `teams` table:
  ```sql
  SELECT name, elo_rating FROM teams WHERE name LIKE '%Indiana%';
  ```
  - If it shows ~2014 → 2026 preseason init has NOT been run yet → save snapshot first
  - If it shows ~1550 → 2026 preseason init was already run → use ranking_history max week
- [ ] Run `utilities/save_final_season_snapshot.py --season 2025` (once implemented)
  - This saves week=999 entries to `ranking_history` for all 235+ teams
  - Safe to re-run; idempotent
- [ ] Enable the feature with initial parameters in `position_weights.json`:
  `weight=0.35`, `mean_regression_factor=0.60`, `returning_regression_scale=0.60`
- [ ] Reinitialize 2026 preseason ratings on the VPS (passing `season=2026`)
- [ ] Save Week 0 snapshot to `ranking_history` for the new preseason
- [ ] Review full top 25 for intuitive correctness:
  - Indiana should appear in top 15
  - Teams that had losing 2025 seasons should rank lower than recruiting alone suggests
  - Alabama/Georgia/Ohio State should remain near the top (both elite recruiting AND strong 2025)
- [ ] Adjust parameters if needed and re-run
- [ ] Document final chosen parameters and rationale

**Expected 2026 Top 10 with full formula (postseason ELO + dynamic regression):**

| Team | Postseason ELO | returning | dynamic_reg | base_formula | Blended |
|------|---------------|-----------|-------------|--------------|---------|
| Indiana | 2014.78 | 0.251 | 0.451 | ~1550 | ~1731\* |
| Georgia | ~1965 | 0.374 | 0.525 | ~1700 | ~1755 |
| Ohio State | ~1924 | 0.308 | 0.485 | ~1700 | ~1741 |
| Alabama | ~1907 | 0.433 | 0.560 | ~1711 | ~1726 |
| Texas Tech | ~1913 | 0.589 | 0.653 | ~1625 | ~1714 |

\*Indiana at ~1730 would be a legitimate top-5 finish based on the postseason ELO.
May need to reduce `prev_season_weight` slightly (e.g., 0.30) to keep the blend reasonable.

**Acceptance Criteria:**
- [ ] Final 2025 postseason ELO is captured in `ranking_history` (week=999)
- [ ] Indiana appears in top 15 of 2026 preseason (ideally top 10)
- [ ] Top 10 contains a mix of elite recruiting programs AND strong 2025 performers
- [ ] No FCS team appears in top 25
- [ ] Parameters documented with rationale in `position_weights.json` comments

---

### Story 30.3: Tune and Validate Regression Parameters
**Priority:** P1
**Effort:** 1–2 hours

**Tasks:**
- [ ] Evaluate whether `previous_season_weight=0.35` produces reasonable top 25
- [ ] Verify teams with losing 2025 records rank appropriately below their recruiting ceiling
- [ ] Adjust parameters if needed and re-run
- [ ] Document final chosen parameters and rationale

**Acceptance Criteria:**
- [ ] Indiana appears in top 15 of 2026 preseason
- [ ] Top 10 contains a mix of elite recruiting programs AND strong 2025 performers
- [ ] No FCS team appears in top 25
- [ ] Parameters documented with rationale in `position_weights.json` comments

---

### Story 30.4: Update Tests
**Priority:** P1
**Effort:** 1–2 hours

**Tasks:**
- [ ] Add unit tests for `save_final_season_snapshot()`:
  - Writes week=999 entries for all teams in the DB
  - Idempotent: re-running updates existing week=999 entries, not duplicating
- [ ] Add unit tests for `_get_previous_season_elo()`:
  - Returns week=999 ELO when available (postseason snapshot)
  - Falls back to highest-week ELO when no week=999 entry exists
  - Returns `None` for team with no previous season data
- [ ] Add unit tests for regression blend in `calculate_preseason_rating()`:
  - `weight=0.0` → identical to current formula (no regression)
  - `weight=0.35` with known `prev_elo`, no `returning_production` → fixed regression
  - `weight=0.35` with known `prev_elo` + `returning_production=0.251` → dynamic regression
  - `weight=0.35` with known `prev_elo` + `returning_production=0.589` → less regression
  - Missing prev season data → falls back to base formula
  - Exception in regression → falls back gracefully
- [ ] Update `test_position_strength_integration.py` to pass `season` param where needed
- [ ] All existing tests continue to pass

**Acceptance Criteria:**
- [ ] New tests cover all cases above
- [ ] Dynamic regression math is verified with known inputs
- [ ] All 630+ existing tests pass

---

## Technical Notes

### Why 0.35 weight and 0.60 base regression?

These are reasonable starting values based on comparable ELO systems:

- **FiveThirtyEight NFL**: Carries ~65% of previous season ELO (less turnover than CFB)
- **College football turnover**: Higher than NFL (4-year eligibility cycle, transfer portal,
  draft departures) → more regression toward mean is appropriate → use 0.60 instead of 0.65+
- **Weight of 0.35**: Previous season provides real signal but shouldn't overwhelm current
  recruiting/roster composition — roughly 1/3 previous season, 2/3 current indicators

These should be validated against historical data once 3+ seasons are in the system.

### Postseason ELO Gap

`ranking_history` is populated during weekly updates. If `save_weekly_rankings()` was
never called for bowl/CFP weeks, the highest entry in `ranking_history` may be
week 16–20 — missing the final playoff results.

**Solution:** `save_final_season_snapshot(season)` writes a week=999 sentinel entry
using the live `teams.elo_rating` **before** any preseason init overwrites it. This
ensures the full postseason ELO (including CFP champion games) is captured.

Real example (2025):
- Indiana `ranking_history` max week = 20 → ELO **1910.72**
- Indiana `teams.elo_rating` after all postseason games → **2014.78**
- Without the snapshot, the regression underestimates Indiana by ~104 ELO points

### Dynamic Regression Formula

```
dynamic_regression = base_regression + (returning_production - 0.5) * returning_regression_scale
dynamic_regression = clamp(dynamic_regression, 0.30, 0.85)
```

At `returning_production = 0.50` (50% returning): `dynamic_regression = base_regression`
At `returning_production = 0.80`: regression increases by `0.30 * scale` (more carry-forward)
At `returning_production = 0.20`: regression decreases by `0.30 * scale` (more mean reversion)

The 0.30–0.85 clamp prevents extreme values: even with 100% returning, some regression
accounts for opponent improvement; even with 0% returning, the coaching staff and
recruiting pipeline still deserve some continuity credit.

### Previous Season Data Availability

- `ranking_history` has data for all 235 teams back through 2024
- Week=999 sentinel entries will be populated by `save_final_season_snapshot()`
  for 2025 forward
- Newly added teams with no `ranking_history` gracefully fall back to base formula
- FCS teams use base of 1300 regardless

### Impact on Existing Tests

`calculate_preseason_rating()` tests pass `team` objects without a season parameter.
Since `season=None` triggers fallback to base formula (same as today), all existing
tests remain valid. New tests specifically test the regression path by passing a season.

---

## Success Metrics

- [ ] 2025 postseason ELO captured in `ranking_history` week=999 for all teams
- [ ] Indiana 2026 preseason rank: top 15 (was outside top 25)
- [ ] Indiana's preseason rating uses 2014.78 (postseason) not 1910.72 (mid-season)
- [ ] Spearman correlation between 2025 final ELO and 2026 preseason rank improves vs current
- [ ] No regressions in existing test suite
- [ ] Parameters documented and committed to `position_weights.json`

---

## Future Enhancements

- **Multi-year regression**: Weight 2 or 3 prior seasons, not just the most recent
- **Coaching change discount**: Reduce previous season weight when head coach changes
- **Automatic tuning**: Script to find optimal weight/regression by backtesting against
  historical data (correlate preseason rating with end-of-season ranking)

---

**Epic Owner:** Bryan Dailey
**Related:** EPIC-029 (exposed issue), EPIC-024 (ranking_history used here)

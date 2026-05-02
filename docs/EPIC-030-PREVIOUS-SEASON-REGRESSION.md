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

### Formula

Add a configurable previous-season blend to `calculate_preseason_rating()`:

```
# Step 1: Calculate base preseason formula (existing)
base_formula = base + recruiting + transfer + returning + position_strength

# Step 2: Get team's final ELO from previous season (from ranking_history)
prev_elo = ranking_history[team][prev_season][final_week].elo_rating

# Step 3: Apply mean regression to previous ELO
#   (pulls extreme values back toward 1500 to account for turnover)
prev_regressed = 1500 + (prev_elo - 1500) * mean_regression_factor

# Step 4: Blend
preseason_rating = (prev_regressed * prev_season_weight)
                 + (base_formula   * (1 - prev_season_weight))
```

### Configuration Parameters (added to position_weights.json)

```json
{
  "previous_season_weight": 0.35,
  "_comment": "How much previous season ELO influences preseason (0=ignore, 1=only prev season)",
  "mean_regression_factor": 0.60,
  "_comment": "How much previous ELO regresses toward 1500 before blending (0=full reset, 1=no regression)"
}
```

### Example: Indiana 2026 Preseason with this formula

```
base_formula    = 1550.0   (recruiting/portal/returning/position)
prev_elo        = 1910.7   (Indiana's final 2025 ELO)
prev_regressed  = 1500 + (1910.7 - 1500) * 0.60 = 1746.4
preseason       = (1746.4 * 0.35) + (1550.0 * 0.65)
                = 611.2 + 1007.5 = 1618.7  ← Top 10, much more reasonable
```

### Graceful Degradation

- If no previous season data exists (new team, first season): use base formula only
- Weight of 0.0 = identical behavior to current formula (safe default)
- Feature starts disabled until validated

---

## Stories

### Story 30.1: Implement Previous Season Regression in Ranking Service
**Priority:** P0
**Effort:** 2–3 hours

**Tasks:**
- [ ] Add `_get_previous_season_elo(team_id, season)` helper to `RankingService`
  - Queries `ranking_history` for the team's highest-week entry in `season-1`
  - Returns `None` if no data exists
- [ ] Add `previous_season_weight` and `mean_regression_factor` to `position_weights.json`
  - Default both to `0.0` initially (no change to current behavior)
- [ ] Modify `calculate_preseason_rating(team, season=None)` to:
  - Accept optional `season` parameter (falls back to active season if None)
  - Call `_get_previous_season_elo()` when `previous_season_weight > 0`
  - Apply blend formula
  - Log the previous season contribution at DEBUG level
- [ ] Update `initialize_team_rating(team, season=None)` to pass season through

**Implementation sketch:**

```python
def _get_previous_season_elo(self, team_id: int, current_season: int) -> Optional[float]:
    """Get team's final ELO from the previous season via ranking_history."""
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
        regression = config.get("mean_regression_factor", 0.60)

        if prev_weight > 0 and season:
            prev_elo = self._get_previous_season_elo(team.id, season)
            if prev_elo:
                prev_regressed = 1500 + (prev_elo - 1500) * regression
                blended = (prev_regressed * prev_weight) + (base_formula_rating * (1 - prev_weight))
                logger.debug(
                    f"{team.name}: prev_elo={prev_elo:.1f} → regressed={prev_regressed:.1f} "
                    f"→ blended={blended:.1f} (weight={prev_weight})"
                )
                return blended
    except Exception as e:
        logger.warning(f"Previous season regression failed for {team.name}: {e}")

    return base_formula_rating
```

**Acceptance Criteria:**
- [ ] `_get_previous_season_elo()` returns correct ELO from ranking_history
- [ ] Returns base formula unchanged when `previous_season_weight = 0.0`
- [ ] Logs previous season contribution at DEBUG level
- [ ] Gracefully returns base formula if previous season data missing or error

---

### Story 30.2: Tune and Validate Regression Parameters
**Priority:** P1
**Effort:** 1–2 hours

**Tasks:**
- [ ] Enable the feature with initial parameters: `weight=0.35`, `regression=0.60`
- [ ] Reinitialize 2026 preseason ratings on the VPS
- [ ] Review full top 25 for intuitive correctness:
  - Indiana should appear in top 15
  - Teams that had losing 2025 seasons should rank lower than recruiting alone suggests
  - Alabama/Georgia/Ohio State should remain near the top (both elite recruiting AND strong 2025)
- [ ] Adjust parameters if needed and re-run
- [ ] Document final chosen parameters and rationale

**Expected 2026 Top 10 with regression (rough estimate):**

| Team | 2025 Final ELO | Base Formula | Blended |
|------|---------------|--------------|---------|
| Georgia | 1965 | ~1700 | ~1775 |
| Ohio State | 1924 | ~1700 | ~1755 |
| Indiana | 1911 | ~1550 | ~1619 |
| Alabama | 1907 | ~1711 | ~1725 |
| Texas Tech | 1913 | ~1625 | ~1697 |
| Ole Miss | 1894 | ~1650 | ~1680 |
| Oregon | 1893 | ~1700 | ~1730 |

**Acceptance Criteria:**
- [ ] Indiana appears in top 15 of 2026 preseason
- [ ] Top 10 contains a mix of elite recruiting programs AND strong 2025 performers
- [ ] No FCS team appears in top 25
- [ ] Parameters documented with rationale in `position_weights.json` comments

---

### Story 30.3: Update Tests
**Priority:** P1
**Effort:** 1–2 hours

**Tasks:**
- [ ] Add unit tests for `_get_previous_season_elo()`:
  - Returns correct ELO when data exists
  - Returns `None` for team with no previous season data
  - Returns latest week's ELO (not an earlier week)
- [ ] Add unit tests for regression blend in `calculate_preseason_rating()`:
  - weight=0.0 → identical to current formula (no regression)
  - weight=0.35 with known prev_elo → correct blended value
  - Missing prev season data → falls back to base formula
  - Exception in regression → falls back gracefully
- [ ] Update `test_position_strength_integration.py` to pass `season` param where needed
- [ ] All existing tests continue to pass

**Acceptance Criteria:**
- [ ] New tests cover the 4 cases above
- [ ] All 630+ existing tests pass

---

## Technical Notes

### Why 0.35 weight and 0.60 regression?

These are reasonable starting values based on comparable ELO systems:

- **FiveThirtyEight NFL**: Carries ~65% of previous season ELO (less turnover than CFB)
- **College football turnover**: Higher than NFL (4-year eligibility cycle, transfer portal,
  draft departures) → more regression toward mean is appropriate → use 0.60 instead of 0.65+
- **Weight of 0.35**: Previous season provides real signal but shouldn't overwhelm current
  recruiting/roster composition — roughly 1/3 previous season, 2/3 current indicators

These should be validated against historical data once 3+ seasons are in the system.

### Previous Season Data Availability

- `ranking_history` has data for all 235 teams back through 2024
- Newly added teams with no `ranking_history` gracefully fall back to base formula
- FCS teams use base of 1300 regardless

### Impact on Existing Tests

`calculate_preseason_rating()` tests pass `team` objects without a season parameter.
Since `season=None` triggers fallback to base formula (same as today), all existing
tests remain valid. New tests specifically test the regression path by passing a season.

---

## Success Metrics

- [ ] Indiana 2026 preseason rank: top 15 (was outside top 25)
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

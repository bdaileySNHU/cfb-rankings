# EPIC-040: Production-Blended Position Strength

**Status:** 📋 Scoped (not started)
**Priority:** Medium
**Created:** 2026-06-06
**Related:** EPIC-039 (roster-based position strength — this builds on it),
EPIC-030 (returning production / previous-season regression)

---

## Problem Statement

After EPIC-039, position strength scores from a team's actual roster — but the
quality signal for each player is still their **recruiting rating** (high-school
pedigree). A former 5★ who has underperformed in college still scores like an
elite player; a 3★ who became an All-American still scores like a 3★.

The goal of EPIC-040 is to blend in **on-field production** so quality reflects
what players have actually done, not just how they were ranked coming out of
high school — moderated by the fact that production is backward-looking and only
exists for players who have already played.

---

## Key Discovery — Data Availability (verified 2026-06-06)

CFBD exposes per-player, per-season production, all keyed by athlete id (which
joins to `roster_players.athlete_id`):

| Endpoint | Covers | Signal |
|---|---|---|
| `/ppa/players/season` | QB, RB, WR, TE | `averagePPA.all`, `totalPPA.all` (predicted points added) |
| `/player/usage` | QB, RB, WR, TE | share of team usage |
| `/stats/player/season` | DL, LB, DB (defensive), K/P (ST), plus offense box score | raw counts: tackles, sacks, TFL, INT, PD, FG, etc. |

**The unavoidable gap: offensive line.** There is no per-player OL production —
line play is measured at the team level (line yards, sack rate, stuff rate), not
per athlete. OL is ~25% of the position weight. So OL will always fall back to
recruiting pedigree.

**Coverage by position group:**

- ✅ QB / RB / WR / TE — PPA + usage (clean, single scale)
- ✅ DL / LB / DB — defensive box score (heterogeneous raw counts, noisier)
- ✅ ST (K/P) — kicking/punting stats
- ❌ OL — recruiting pedigree only (no per-player data exists)

**Production is backward-looking.** 2024 production informs 2025 roster strength.
True freshmen and transfers without prior FBS snaps have no production → they
fall back to recruiting. So a blend is really "production where it exists,
recruiting everywhere else."

---

## Proposed Design

Per rostered player, compute a **blended quality score (0–100)**:

```
quality = w_prod * production_score + (1 - w_prod) * recruiting_score   # if production exists
quality = recruiting_score                                              # otherwise
```

- `recruiting_score` = the existing EPIC-038/039 normalization of the recruiting
  rating (already 0–100).
- `production_score` = a per-position-family mapping to 0–100:
  - **Skill (QB/RB/WR/TE):** normalize `averagePPA.all` (and/or usage) across the
    FBS population to a percentile → 0–100.
  - **Defense (DL/LB/DB):** a weighted composite of defensive counts
    (sacks, TFL, tackles, INT, PD) normalized to FBS percentiles per group.
  - **ST:** FG made / accuracy, punting average.
  - **OL:** no production → always recruiting.
- `w_prod` is config-driven (e.g. 0.5) and can taper by class year (a senior's
  production is more trustworthy than a redshirt freshman's small sample).

Aggregate per position group exactly as today (top-N average → weighted sum →
`max_bonus`). The blend changes only how each player's quality is computed.

### Data model

Extend `roster_players` (or a sibling `roster_production` table) with resolved
production fields snapshotted at import:

```
production_score   FLOAT NULL    -- 0–100, per-position normalized
production_source  VARCHAR       -- 'ppa' | 'defense' | 'st' | 'none'
blended_rating     FLOAT NULL    -- final 0–100 used by scoring
```

Storing the blend at import keeps scoring a single fast query and makes the
percentile normalization (which needs the whole FBS population) a batch step.

---

## Stories (proposed)

1. **CFBD production client methods** — `get_player_ppa_season`,
   `get_player_usage`, `get_player_season_stats`; unit tests.
2. **Production normalization** — per-position-family mapping of raw production to
   0–100 FBS percentiles. Pure functions + tests on fixture data.
3. **Production import / blend** — fetch production for the season, normalize,
   compute `blended_rating`, snapshot onto `roster_players`. ~3 calls/team/season.
4. **Scoring uses blended rating** — `position_service` reads `blended_rating`
   when `source == "roster"` and a new `"blend": true` flag is set; config knobs
   for `w_prod` and class-year taper. Recruiting-only remains the fallback.
5. **Endpoint + radar** — report whether each group used production or pedigree;
   optionally a second radar ring (pedigree vs production). Tests.
6. **Tuning + runbook** — correlate blended scores with end-of-season ELO across
   2021–2024 to pick `w_prod`; document the import in the season runbook.

---

## Risks & Open Questions

- **OL stuck on pedigree.** ~25% of the weighted formula can't use production.
  Acceptable, but means the blend is partial by construction.
- **Heterogeneous, noisy defensive stats.** Turning raw counts into a fair
  per-position quality score is judgment-heavy and the most error-prone part.
  Scheme and snap counts confound raw totals.
- **Backward-looking bias.** Production rewards returning players and is blind to
  breakout freshmen/transfers — partly the opposite blind spot of recruiting,
  which is arguably why blending helps, but worth validating.
- **Another preseason ELO shift.** Like EPIC-038/039, changes preseason ratings;
  re-verify the top 25 and re-tune `max_bonus` / `w_prod` together.
- **API cost.** ~3 extra calls/team/season (~400/season) — fine within quota.

---

## Recommendation

Worth doing, but **scope it as skill-positions-first**: PPA-based blending for
QB/RB/WR/TE is clean, high-signal, and covers the most valuable single position
(QB, 30% weight). Defensive box-score blending is a noisier second phase, and OL
stays on pedigree regardless. Suggest building Stories 1–4 for the skill
positions, validating the top-25 impact, then deciding whether the defensive
phase earns its complexity.

**Effort:** Large — 6 stories, with Story 2 (normalization) and Story 6 (tuning)
carrying most of the modeling risk.

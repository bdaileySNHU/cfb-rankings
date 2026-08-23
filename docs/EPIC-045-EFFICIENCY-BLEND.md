# EPIC-045: CORE-Style Efficiency Blend

**Status:** ✅ Implemented (2026-08-09) — pending accuracy validation on live weeks
**Priority:** Medium
**Related:** EPIC-040 (per-player PPA for position strength — same data family, different grain)
**Source:** [Introducing CORE college football ratings](https://radsportsanalytics.com/blog/introducing-core-college-football-ratings/)

---

## Problem Statement

The Modified ELO rating is entirely **result-driven**: who won, by how much, against
whom. It has no view of *how* a team won. A team that wins five one-score games
against weak opponents rates identically to a team that wins five blowouts, and
ELO cannot tell the difference between "good" and "lucky" until the luck runs out.

CORE (Context & Opponent-Relative Efficiency) measures the other half: points
created and allowed per play, adjusted first for situation (down, distance, field
position, score, clock, home/away) and then for opponent strength across the whole
schedule network. It is **efficiency-driven** and orthogonal to won-lost record.

Blending the two gives a rating neither signal produces alone.

---

## What We Did *Not* Build

CORE itself is published as a blog, not a feed — there is nothing to consume. And
rebuilding it from play-level data would mean pulling every FBS scrimmage play,
fitting a context model, and running a regularized joint offense/defense
regression.

CFBD already does both CORE stages and publishes the result at `GET /ppa/teams`:
`offense.overall` and `defense.overall` are opponent-adjusted PPA per play. We
consume those instead. One API call per import run.

---

## Design

### Data

`teams.offense_ppa` / `teams.defense_ppa` (nullable floats), refreshed by
`src/importers/efficiency.py::import_team_efficiency` during every pipeline run.
CFBD returns season-to-date values, so calling it in week N gives a point-in-time
rating with no lookahead.

### Scale — why standardizing, not a constant

The obvious mapping is a fixed points-per-play constant: net PPA × ~70 plays/game
converted at this model's own 100 ELO ≈ 7 points, giving ~1000 ELO per unit of net
PPA. **Measured against real 2025 data, that is badly wrong for this system:**

| | span across FBS |
|---|---|
| this model's ELO | 1482 → 1696 (~215 points) |
| net PPA at 1000 ELO/unit | 1210 → 1840 (~630 points) |

ELO here is far more compressed than the theoretical conversion assumes, so a fixed
constant would have injected roughly 3× the intended spread — a nominal 25% weight
behaving like a majority stake, and the blend would have thrown teams ±43 ranking
places.

Instead both signals are standardized. `efficiency_scale()` computes the FBS mean
and standard deviation of ELO and of net PPA, and `efficiency_rating()` places each
team on ELO's own mean and spread by z-score. One standard deviation of efficiency
is worth exactly one standard deviation of ELO, `EFFICIENCY_WEIGHT` means what it
says, and the mapping recalibrates itself as ELO disperses through the season.

### The blend

```
effective_rating = (1 - w) * elo_rating + w * efficiency_rating
```

`w = EFFICIENCY_WEIGHT` (env var, default **0.25**). Falls back to pure ELO when:

- `EFFICIENCY_WEIGHT` is 0 — the kill switch
- the team has no PPA data (preseason, FCS, uncovered team)
- the week is below `EFFICIENCY_MIN_WEEK` (4) — adjusted PPA is unstable on a
  handful of games and CFBD's opponent adjustment has little schedule network yet
- fewer than 20 rated teams exist, or either signal has no spread to standardize
- anything at all goes wrong reading the population — the blend is an enhancement,
  never a hard dependency of prediction

### Where it applies

| Path | Rating used |
|---|---|
| `save_weekly_rankings` → `ranking_history.elo_rating` | **blended** |
| `_calculate_game_prediction` / `generate_predictions` | **blended** |
| `create_and_store_prediction` → `*_elo_at_prediction` | **blended** (records what the prediction was made from) |
| `process_game` ELO update math | **pure ELO** |
| `calculate_sos` | **pure ELO** |
| `save_final_season_snapshot` (week 999) → next-season carryover | **pure ELO** |

`teams.elo_rating` is never written with a blended value. The blend is applied at
read time only, so efficiency never compounds into itself through the update loop,
and setting `EFFICIENCY_WEIGHT=0` reverts the system completely with no data
repair. Rankings pick the blend up for free because they already read from
`ranking_history`.

---

## Observed Effect (2025 final, w=0.25)

Efficiency span lands at 1477 → 1703 against ELO's 1482 → 1696 — matched, as
intended. Movement is a reorder, not a rescale: ±25 ranking places at the extremes,
a few places inside the top 25.

Up: Ohio State, Indiana, Texas Tech, Utah — efficiency stronger than record.
Down: LSU, Texas, Alabama — record stronger than efficiency.

---

## Backtest

`scripts/backtest_efficiency_blend.py` replays a season week by week against a
throwaway copy of the database: at week N it predicts every game from ELO replayed
over weeks 1..N-1 and efficiency through week N-1, then processes week N and
advances. No lookahead.

`/ppa/teams` cannot be queried retroactively — it only ever returns today's
season-to-date numbers — so the harness rebuilds weekly efficiency from
`/ppa/games` (one API call per season, cached to `data/`, so re-runs cost nothing).
The proxy is the plain running mean of per-game net PPA, which correlates **0.987**
with CFBD's adjusted values over 2025 at near-identical spread (sd 0.137 vs 0.132).
Refitting CORE's opponent adjustment scored *worse* (0.94–0.98): at full season FBS
schedules balance out enough that the adjustment is a small correction. Since the
blend standardizes to z-scores, only correlation matters.

### Results — 2024 + 2025, 1536 games

Pure ELO baseline: accuracy **0.6927**, Brier **0.1948**.

| w | acc (min_wk 4) | Brier (min_wk 4) |
|---|---|---|
| 0.00 | 0.6927 | 0.1948 |
| 0.10 | 0.6992 | 0.1934 |
| 0.15 | 0.6999 | 0.1928 |
| **0.20** | **0.7005** | 0.1923 |
| 0.25 | 0.6986 | 0.1919 |
| 0.30 | 0.6992 | 0.1915 |
| 0.40 | 0.6940 | 0.1912 |
| 0.50 | 0.6960 | 0.1913 |

The blend beats pure ELO on Brier at **every** weight and every gate tested. Gains
are real but modest: about +0.8pp accuracy (~12 games in 1536) and ~1.5% Brier
reduction at the peak.

Brier keeps improving past w=0.30, but that is entirely a 2024 effect — in 2025,
w≥0.40 *reduces* accuracy (0.7093 at w=0.50 vs 0.7187 baseline). The seasons only
agree in the 0.10–0.30 band, so the high end is not trustworthy. **w=0.20–0.25 is
the robust choice**; the shipped default of 0.25 sits inside it and needs no change.

### The week gate: keep it at 4

Efficiency ordering is unstable early — through week 4 it correlates only 0.73 with
where it ends up, not reaching 0.9 until week 9. That argued for raising
`EFFICIENCY_MIN_WEEK`. **The backtest says otherwise:** `min_week=4` matches or
beats 6, 8 and 10 at every weight, and 10 is consistently the worst. Noisy early
efficiency still carries more information than the preseason-dominated ELO it is
being blended against. The gate stays at 4.

---

## Open Items

- **Forward validation still matters.** The backtest rests on two seasons and on a
  proxy validated only at full-season granularity — there is no historical CFBD
  snapshot to check the week-6 proxy against, and unbalanced early schedules are
  exactly where opponent adjustment earns its keep. Keep tracking
  `predictions.was_correct` and Brier on live weeks; production uses the real
  adjusted `/ppa/teams` values, which should be no worse than the proxy.
- **Tuning knob.** `EFFICIENCY_WEIGHT` is env-driven so it can move without a
  redeploy as live accuracy accumulates.
- Efficiency is not surfaced in the API or frontend yet. The columns are there if
  a team-detail offense/defense split is wanted later.

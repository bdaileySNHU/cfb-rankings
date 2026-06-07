# EPIC-039: Roster-Based Position Strength

**Status:** ✅ Complete (2026-06-06)
**Priority:** Medium
**Created:** 2026-06-06
**Related:** EPIC-038 (position radar — consumer of this data), EPIC-030
(returning production / previous-season regression), EPIC-033 (data pipeline)

---

## Problem Statement

Position group strength — the data behind the EPIC-038 radar and the preseason
ELO `position_strength_bonus` — is currently derived from **recruiting class
signings** (CFBD `/recruiting/players`), not the actual roster. This produces
three concrete inaccuracies:

1. **Departed players still count.** There is no active/departed concept. A 5★
   QB who transferred out or left for the NFL still contributes to that team's
   QB score.
2. **Incoming transfers are invisible.** Portal additions aren't HS recruits, so
   a team that reloaded through the portal looks artificially weak.
3. **Only signees, not the roster.** Scoring pools recent recruiting classes
   (currently 2024 + 2025) and ignores everyone else — upperclassmen developed
   over 3–4 years, walk-ons who earned a starting job, etc.

Turnover is handled only bluntly elsewhere in the preseason formula
(`returning_production` and `transfer_portal_rank` are team-wide tiers), never at
the position-group level. The radar therefore measures *recruiting pedigree by
position*, not *who is on the team*.

---

## Goal

Score position groups from each team's **actual current roster** for the active
season, with recruiting ratings joined on, so the radar and the preseason bonus
reflect real roster composition — transfers in, departures out, all four class
years.

---

## Key Discovery — Feasibility (verified 2026-06-06)

CFBD `GET /roster?team={t}&year={y}` returns the real roster. For Georgia 2025:

- **132 players**, each with `id` (athlete id), `position`, `year` (class:
  1=FR … 5), and `recruitIds` (links to recruiting records).
- The roster carries **no rating** — it must be joined from recruiting data.

**Join strategy (chosen): athlete-id.** Our `players.cfbd_athlete_id` already
stores the recruiting record's `athleteId`, and `roster.id` is that same athlete
id. So `roster.id == players.cfbd_athlete_id` resolves a rating directly — no new
join column required. (`roster.recruitIds` → recruiting `id` is an alternate join
but would require storing the recruiting record `id`, which we don't today.)

**Coverage findings:**

- Only **76 / 132** roster players have any recruiting link (walk-ons / unrated
  have none) — acceptable, because scoring uses *top-N rated players per group*.
- With only 2024 + 2025 recruiting imported, the athlete-id join resolves
  **46 / 132** — and **all of them are FR/SO**. Juniors and seniors are 2021–2023
  recruits we haven't imported.

➡️ **Prerequisite:** import recruiting classes back ~5 years (2021–2025) so every
class year on a current roster can resolve a rating.

---

## Design

### Data model

Add a season-scoped roster table, keeping "recruiting class" (historical
pedigree) separate from "roster this season" (membership):

```
roster_players
  id            INTEGER PK
  season        INTEGER          -- e.g. 2026
  team_id       INTEGER FK teams
  athlete_id    INTEGER          -- CFBD roster.id
  name          VARCHAR
  position      VARCHAR(10)
  class_year    INTEGER          -- 1..5 (FR..)
  rating        FLOAT NULL       -- resolved from players via athlete-id join
  source        VARCHAR          -- 'recruiting-join' | 'unrated'
  created_at    DATETIME
  UNIQUE(season, team_id, athlete_id)
  INDEX(season, team_id, position)
```

`rating` is resolved at import time (snapshot), so scoring is a single fast query
and doesn't depend on which recruiting years happen to be loaded at read time.

### Scoring change

`position_service.get_position_group_scores()` gains a roster-based path:

- When roster data exists for the active season, select top-N **roster** players
  per group (by joined `rating`), normalize with the existing
  `_normalize_rating()` (EPIC-038 fix), and aggregate as today.
- Fall back to the current recruiting-class path when no roster is imported, so
  nothing breaks before the backfill runs. Gate behind a config flag
  (`position_weights.json: "source": "roster" | "recruiting"`).

### Why this fixes the three problems

- **Departures:** off the roster ⇒ excluded automatically.
- **Transfers in:** appear on the new team's roster; `recruitIds`/athlete-id
  still resolves their original recruiting rating.
- **Full roster:** all class years included once 2021–2025 recruiting is loaded.

---

## Stories

### Story 39.1 — CFBD `get_roster()` client method
Add `get_roster(team, year)` to `src/integrations/cfbd_client.py` with usage
tracking; unit tests with a mocked response.

### Story 39.2 — Backfill recruiting classes 2021–2025
Run `utilities/import_player_data.py` for 2021–2024 (2025 already loaded) so
upperclassmen resolve. ~135 teams × 4 years ≈ 540 CFBD calls (one-time). Verify
join coverage climbs from ~46 → most of the 76 linked players for a sample team.

### Story 39.3 — `roster_players` table + import utility
Migration (`migrations/migrate_add_roster_table.py`) + model +
`utilities/import_roster.py --year` that pulls each FBS roster, joins ratings via
athlete-id, and writes snapshots. ~135 calls/season.

### Story 39.4 — Roster-based scoring path
Extend `position_service` with the roster path + config flag; recruiting path
remains the fallback. Tests covering: transfer-in counted, departed excluded,
unrated skipped, fallback when no roster.

### Story 39.5 — Wire endpoint + radar; relabel
`/api/teams/{id}/position-strength` reports the source used and `season`. Radar
header reflects "current roster" vs "recruiting" honestly. Tests.

### Story 39.6 — Pipeline + runbook
Fold roster import into the preseason refresh (alongside EPIC-033 Story 33.2) and
document in `docs/SEASON-RUNBOOK.md`. Decide refresh cadence (preseason + maybe
post-portal windows).

---

## Risks & Open Questions

- **Preseason ELO shift (again).** Position scores will change, moving preseason
  ratings. Re-verify the top 25 after rollout; revisit whether `max_bonus: 150`
  is still right. (EPIC-038 already surfaced how large this lever is.)
- **Rating is still pedigree, not production.** A roster of former 5★ recruits
  who underperform still scores high. A later enhancement could blend in usage /
  returning production per position. Out of scope here.
- **`recruitIds` / `athleteId` nulls.** ~42% of a roster has no recruiting link;
  those players are simply excluded from top-N (acceptable). Some transfers from
  non-FBS or older classes may not resolve.
- **Roster timing.** CFBD roster for year N reflects offseason moves with some
  lag; early-draft departures and late portal moves may not be instantaneous.
- **API quota.** One-time backfill (~540) + ~135/season is well within the 30k
  monthly limit, but worth batching.

---

## Effort

**Medium–Large — 6 stories.** Backbone is Stories 39.2 (data backfill) and 39.3
(roster table + import); the scoring/endpoint/radar changes are small once the
roster snapshot exists. No frontend rebuild needed — EPIC-038's radar consumes
whatever the endpoint returns.

---

## As-Built (2026-06-06)

All six stories complete.

- **39.1** `CFBDClient.get_roster(team, year)` → `/roster`; 7 unit tests
  (`tests/unit/test_cfbd_roster_api.py`).
- **39.2** Backfilled recruiting classes 2021–2025 locally. Coverage for a sample
  team (Georgia 2025) rose from 46→73 of 132 rostered players resolving a rating
  (73 of the 76 with any recruiting link; the rest are walk-ons, excluded).
- **39.3** `RosterPlayer` model + `migrations/migrate_add_roster_table.py` +
  `utilities/import_roster.py` (idempotent per season/team; resolves rating via
  athlete-id). Full 2025 import: 15,476 rows across 135 teams, 5,741 rated.
- **39.4** `get_position_group_scores()` / `calculate_position_strength()` gained a
  `season` arg and a roster path gated by `position_weights.json: "source"`
  (default `"roster"`), with per-team fallback to recruiting. `resolve_roster_season()`
  helper. 5 new unit tests (transfer-in counted, departed excluded, unrated
  skipped, fallback).
- **39.5** `/api/teams/{id}/position-strength` now reports `source` and `season`;
  the radar header shows "{year} roster" vs "{year} class". 2 endpoint tests.
- **39.6** `docs/SEASON-RUNBOOK.md` updated: 5-class recruiting backfill + new
  step 1d.2 (roster import after recruiting, before preseason finalize).

**Design choices made during build:**
- Join is athlete-id (`roster.id` == `players.cfbd_athlete_id`) — no schema change
  to the join key.
- `source` defaults to `"roster"`; recruiting remains the automatic per-team
  fallback when a team has no snapshot, so nothing breaks pre-import.
- Rating is still recruiting *pedigree*, not on-field production (future work).

**Caveat carried forward:** enabling roster scoring changes preseason position
scores, which moves preseason ELO. Re-verify the top 25 after the production
roster import (runbook step 1f) and revisit whether `max_bonus: 150` is right.

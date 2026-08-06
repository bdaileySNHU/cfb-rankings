# EPIC-033: 2026 Season Data Pipeline

**Status:** ⏳ In Progress (33.1–33.3 complete; 33.4 and 33.5 remain)
**Priority:** High
**Created:** 2026-05-04
**Target:** Before Week 1 kickoff (~Aug 29, 2026)
**Related:** EPIC-029 (preseason setup), EPIC-019 (incremental data updates)

---

## Problem Statement

The 2026 season exists in the database (week 0, preseason) but the data
pipeline for the live season is not fully automated. Today, importing game
schedules, results, and preseason roster data requires manually running scripts
with specific commands. As Week 1 approaches we need:

1. **2026 game schedule imported** — all FBS matchups loaded into `Game` table
2. **Recruiting/portal/returning production data current** — 2026 player data
   drives the preseason ELO; needs to be as fresh as possible before kickoff
3. **Automated weekly result imports** — after each game weekend, results should
   flow in without a manual deploy step
4. **Pipeline health monitoring** — visibility into what imported, what failed,
   and whether ELO updates ran successfully
5. **Season transition procedure documented** — clear runbook so the hand-off
   from preseason → Week 1 is repeatable in future years

---

## Goals

1. Import the full 2026 FBS schedule
2. Refresh 2026 recruiting, transfer portal, and returning production data
3. Create an automated weekly import job (cron on VPS) for game results
4. Add an admin API endpoint to trigger/inspect imports manually
5. Document the full season-start and weekly-update runbook

---

## Stories

### Story 33.1: Import 2026 Game Schedule ✅
**Priority:** P0 — blocks everything else
**Effort:** 1–2 hours
**Completed:** 2026-05-04 — 94 Week 1 games imported. Remaining weeks will
populate automatically via the Monday cron job as CFBD publishes them.

Import all 2026 FBS regular-season and known bowl/CFP matchups from CFBD API.

**Tasks:**
- [x] Run `import_games` utility (check `utilities/` for existing script or EPIC-019 tooling)
- [x] Verify week assignments are correct (Week 1 = Aug 29–30)
- [x] Confirm neutral site flags are set correctly (Kickoff Classic, etc.)
- [x] Check that FCS opponents are marked correctly
- [x] Verify game count matches CFBD (roughly 900 FBS regular season games)
- [x] Commit any script changes needed to make the import idempotent

**Acceptance Criteria:**
- [x] `SELECT COUNT(*) FROM games WHERE season=2026` returns ~900+ — 777 as of
  2026-08-06; CFBD has not published the full slate yet and the Monday cron
  continues to backfill
- [x] Week 1 games present and dated correctly — earliest kickoff
  2026-08-29 16:00 UTC (noon ET)
- [x] No duplicate games on re-run — the 2026-08-06 re-run added 5 games and
  skipped 114 already-present/FCS matchups

---

### Story 33.2: Refresh 2026 Preseason Data ✅
**Priority:** P0
**Effort:** 2–3 hours
**Completed:** 2026-08-06 — run against production. CFBD published 2026
recruiting, returning production, transfer portal, and roster data in early
August, as predicted on May 4.

Ensure recruiting rankings, transfer portal points, and returning production
percentages reflect the latest available 2026 data before ELO preseason ratings
are locked in.

**Tasks:**
- [x] Re-run `utilities/import_player_data.py --year 2026` with latest CFBD data
- [x] Verify 247Sports recruiting composite rankings loaded for 2026 class
- [x] Verify transfer portal entries for 2026 are current
- [x] Re-run preseason ELO calculation (`utilities/finalize_2026_preseason.sh`)
- [x] Compare top-25 preseason ratings before/after — confirm changes are sensible
- [x] Update `ranking_history` week-0 snapshots with recalculated values

**Acceptance Criteria:**
- [x] Player data table has 2026 entries for all major programs
- [x] Preseason ELO rankings updated and snapshot saved
- [x] Top 5 teams are reasonable — Oregon, Ohio State, Texas, Georgia, Notre Dame

#### What was actually wrong

The epic assumed this was only a data-freshness task. It was worse: **every FBS
team was carrying sentinel values**, not stale ones.

```sql
SELECT SUM(recruiting_rank=999), SUM(returning_production=0.5), COUNT(*)
  FROM teams WHERE is_fcs=0;
-- before: 136|136|136
```

`recruiting_rank=999` and `returning_production=0.5` are the "missing data"
defaults in `src/importers/teams.py`. 2026 preseason ELO was being computed from
transfer portal points and previous-season regression alone, with no recruiting
or returning-production signal at all. `roster_players` had no 2026 rows either,
so `position_service.py` was silently falling back to the 2025 roster (see the
most-recent-season fallback around `position_service.py:218-228`).

#### The sequence that fixed it

Run in this order — steps 2–4 must precede step 5, and step 4 must follow step 3.

```bash
cd /var/www/cfb-rankings

# 0. Back up first. Step 1 overwrites team columns in place and there is no
#    dry run for it (see Gotchas). `.backup` is safe on a live SQLite file.
sudo mkdir -p /var/backups/cfb-rankings
BK=/var/backups/cfb-rankings/cfb_rankings.$(date +%F-%H%M).pre-epic033.db
sudo sqlite3 cfb_rankings.db ".backup '$BK'"
sudo sqlite3 "$BK" "PRAGMA integrity_check;"   # expect: ok

# 1. Team-level preseason inputs (recruiting rank, returning production, portal)
#    plus any newly published schedule.
sudo -u www-data venv/bin/python import_real_data.py --season 2026

# import_player_data.py / import_roster.py / import_production.py do NOT call
# load_dotenv(), so CFBD_API_KEY must be handed across the sudo boundary.
set -a; source .env; set +a

# 2. 2026 recruiting class -> players
sudo -u www-data CFBD_API_KEY="$CFBD_API_KEY" venv/bin/python \
  utilities/import_player_data.py --year 2026 --force

# 3. Real 2026 rosters -> roster_players (EPIC-039)
sudo -u www-data CFBD_API_KEY="$CFBD_API_KEY" venv/bin/python \
  utilities/import_roster.py --year 2026 --force

# 4. PPA production blend -> blended_rating (EPIC-040)
sudo -u www-data CFBD_API_KEY="$CFBD_API_KEY" venv/bin/python \
  utilities/import_production.py --roster-season 2026 --production-year 2025

# 5. Re-rate all FBS teams and refresh the ranking_history snapshots
bash utilities/finalize_2026_preseason.sh 2026

sudo systemctl restart cfb-rankings
```

Roughly 275 CFBD calls total, almost all in steps 2 and 3. Well inside the
30,000/month quota.

#### Production results (2026-08-06)

| Table | Before | After |
|---|---|---|
| `teams` recruiting sentinels (FBS) | 136 of 136 | 0 |
| `teams` returning-production defaults | 136 of 136 | 4 |
| `players` 2026 class | absent | 2,200 |
| `roster_players` 2026 | absent | 14,946 rows / 136 teams / 6,543 rated |
| production blend | — | 5,635 blended, 4,027 recruiting-only, 5,284 no signal |
| `games` 2026 | 772 | 777 |

Preseason top 5 moved from `Georgia, Alabama, Texas A&M, Ohio State, Texas`
(a May 11 snapshot) to `Oregon 1829.7, Ohio State 1822.7, Texas 1802.1,
Georgia 1801.5, Notre Dame 1795.2`.

Four teams have no CFBD returning-production entry and keep the 0.5 default:
Bowling Green, Buffalo, Massachusetts, UTEP.

Production also lacks the 2021 recruiting class, so 6th-year players on a 2026
roster resolve no recruiting rating — 43.8% of roster rows rated vs 45.2% on a
dev database that had 2021. Importing it costs ~133 calls if that matters later.

#### Three bugs found in `finalize_2026_preseason.sh`

All fixed (PR #8, PR #9). The script had never been run against an existing
season before, so none of these had surfaced.

1. **Missing `season` argument.** It called `initialize_team_rating(team)` with
   no season, skipping previous-season regression (EPIC-030) and the
   season-aware position-strength bonus — silently undoing the fixes in
   `d1e2738` and `8a42fcb`. Signature is
   `initialize_team_rating(team, season=None)` (`src/core/ranking_service.py:333`).
2. **`set -e` abort.** `start_new_season.py` exits non-zero on "Season already
   exists", killing the run before any re-rating. Now guarded by an explicit
   existence check.
3. **Stale `current_week` snapshot.** Only week 0 was refreshed, but
   `get_current_rankings()` serves the season's `current_week`
   (`ranking_service.py:863`). Step 1 rewrites the week-1 snapshot with
   pre-refresh ratings, so the API kept serving the old numbers after an
   otherwise successful run. Both week 0 and `current_week` are now saved.

A fourth surfaced during the prod run itself: the script exported `SEASON`, but
`sudo` scrubs the environment, so every embedded Python block died on
`KeyError: 'SEASON'`. The local rehearsal had used the `CFB_PYTHON` override,
which involves no sudo — the tested path and the shipped path were not the same
path. Fixed in PR #9.

#### Gotchas for next season

- **`--validate-only` is not a dry run for teams.** `import_teams()` runs and
  commits before the validate branch (`src/importers/pipeline.py:174`). Step 1
  always writes. The backup is the only undo.
- **`teams` is not season-scoped.** One row per team, so refreshing for 2026
  overwrites the 2025 values. Reprocessing an earlier season after this will use
  the current year's recruiting and returning-production inputs.
- **These utilities don't load `.env`.** `import_player_data.py`,
  `import_roster.py`, and `import_production.py` read `CFBD_API_KEY` from the
  environment only. `import_real_data.py` and the API server do call
  `load_dotenv()`.
- **Rehearse against a scratch DB**, not just any non-prod DB:
  `DATABASE_URL="sqlite:///$PWD/rehearsal.db"` in front of any of these steps
  redirects all writes. `finalize_2026_preseason.sh` also honours `CFB_ROOT` and
  `CFB_PYTHON` for local runs — but note that the override path bypasses sudo,
  which is exactly how bug 4 above escaped the rehearsal.

---

### Story 33.3: Automated Weekly Import Cron Job ✅
**Priority:** P1
**Effort:** 3–4 hours
**Completed:** 2026-05-04 — `utilities/weekly_update.sh` created and cron entry
active (`0 9 * * 1`) on VPS. Logs to `/var/log/cfb-rankings/weekly.log`.
Dry-run tested and two bugs fixed 2026-08-06; log rotation added the same day.

> **⚠ Two weekly update paths exist.** `deploy/` also ships a systemd timer
> (`cfb-weekly-update.timer`) that runs a *different* script,
> `scripts/weekly_update.py`, as `www-data` on Sunday 22:00 UTC, logging to
> `weekly-update.log`. The cron entry runs `utilities/weekly_update.sh` as
> `bdailey` on Monday 09:00, logging to `weekly.log`. If both are enabled the
> import runs twice a week from two code paths. Confirm which is actually live
> before Week 1:
> ```bash
> crontab -l | grep weekly
> systemctl list-timers cfb-weekly-update.timer
> ```

Set up a cron job on the VPS that runs every Monday morning to:
1. Fetch the previous week's game results from CFBD
2. Process them through the ELO algorithm
3. Update rankings
4. Restart the API service if needed

**Tasks:**
- [x] Create `utilities/weekly_update.sh` (or Python equivalent) that:
  - Calls CFBD for results of the just-completed week
  - Inserts/updates scores in `Game` table
  - Runs ELO processing for those games
  - Saves a `ranking_history` snapshot for the week
  - Logs success/failure with timestamp
- [x] Add cron entry on VPS: `0 9 * * 1 /var/www/cfb-rankings/utilities/weekly_update.sh >> /var/log/cfb-rankings/weekly.log 2>&1`
- [x] Test the script manually against Week 1 results before going live — done
  2026-08-06 against a scratch DB copy. Found a data-loss bug: the ELO step
  looped `save_weekly_rankings()` over every completed week, overwriting all
  prior snapshots with current ratings (2025 week 14 went from Ohio State
  1950.4 to Ole Miss 1696.0). Same bug in `src/importers/pipeline.py` and the
  admin reprocess endpoint. Fixed and pinned by
  `tests/unit/test_weekly_snapshot.py`.
- [x] Add log rotation for `/var/log/cfb-rankings/weekly.log` —
  `deploy/logrotate-cfb-rankings`, installed by `deploy/setup.sh`:
  ```bash
  sudo cp deploy/logrotate-cfb-rankings /etc/logrotate.d/cfb-rankings
  sudo logrotate -d /etc/logrotate.d/cfb-rankings   # dry run, prints the plan
  ```
  Globs `/var/log/cfb-rankings/*.log` because three jobs write there — see the
  note below on the two weekly update paths.

**Acceptance Criteria:**
- [x] Script runs end-to-end without manual intervention
- [ ] ELO ratings updated after a dry-run against known results — not yet
  exercised against real 2026 results
- [x] Cron entry confirmed active (`crontab -l`)
- [x] Log file created and readable

---

### Story 33.4: Admin Import API Endpoint
**Priority:** P1
**Effort:** 2 hours

Add a protected API endpoint so imports can be triggered or inspected from
the browser without SSH access.

**Tasks:**
- [ ] `POST /api/admin/import/results?season=X&week=Y` — triggers CFBD fetch
  and ELO processing for a specific week; requires `X-Admin-Key` header
- [ ] `GET /api/admin/import/status` — returns last import timestamp, games
  processed, any errors; requires `X-Admin-Key`
- [ ] Store import log in a simple `ImportLog` table or a JSON file
- [ ] Return meaningful errors (CFBD API key missing, week not found, etc.)

**Acceptance Criteria:**
- [ ] `POST` with valid admin key triggers import and returns summary
- [ ] `POST` without key returns 403
- [ ] `GET /status` shows last run time and result

---

### Story 33.5: Season Runbook Documentation — mostly done, needs a refresh
**Priority:** P2
**Effort:** 1–2 hours

Write a clear, step-by-step runbook so the preseason → Week 1 transition and
each subsequent week's update is documented and repeatable.

`docs/SEASON-RUNBOOK.md` was written 2026-06-06 and covers all eight required
areas across 534 lines. It predates the 2026-08-06 production run, so its
preseason section is missing what that run uncovered.

**Tasks:**
- [x] Create `docs/SEASON-RUNBOOK.md` covering:
  - Pre-season checklist (schedule import, player data, preseason ELO) — §1
  - Week 1 activation steps (flip season to active, verify schedule) — §2
  - Weekly update procedure (manual and automated) — §3, §4
  - End-of-season procedure (bowl games, CFP, final snapshot, archive) — §5, §6
  - Troubleshooting (missed week, bad data, rollback) — §8
- [x] Reference existing utility scripts with exact commands
- [x] Note environment variables required (`CFBD_API_KEY`, `ADMIN_SECRET`) — §7
- [ ] **Fold in the 2026-08-06 findings** (see Story 33.2 above):
  - `import_real_data.py --season <year>` belongs in §1 as an explicit step —
    without it every team keeps sentinel recruiting/returning values
  - `--validate-only` does not protect the `teams` table
  - `CFBD_API_KEY` must cross the sudo boundary for the three utilities that
    skip `load_dotenv()`
  - `.backup` before step 1, with the restore command spelled out

**Acceptance Criteria:**
- [x] A developer with no prior context can follow the runbook
- [x] All commands tested and verified
- [x] Covers at least pre-season, weekly, and end-of-season phases

---

## Technical Notes

### Existing tooling to reuse
- `import_real_data.py --season <year>` — teams (recruiting rank, returning
  production, transfer portal) plus schedule; wraps `src/importers/`
- `utilities/import_player_data.py` — player/recruiting data from CFBD
- `utilities/import_roster.py` — real rosters into `roster_players` (EPIC-039)
- `utilities/import_production.py` — PPA production blend (EPIC-040); must run
  after `import_roster.py` for the same season
- `utilities/finalize_2026_preseason.sh [year]` — re-rates all FBS teams and
  refreshes the `ranking_history` snapshots
- `utilities/setup_2026_preseason.sh` — initial 2026 season setup
- `utilities/reprocess_season.py` — reprocess all games for a season
- EPIC-019 incremental update scripts (check `src/` for weekly import logic)

### Data dependency order
`teams` inputs and `players` are independent, but position strength is a chain:
`players` → `roster_players` (rating resolved by athlete-id join) →
`blended_rating` → preseason bonus. `position_weights.json` currently has
`source=roster, blend=true`, so a missing roster season makes
`position_service.py` fall back to the most recent season it does have — quietly,
with no error.

### CFBD API
- Base URL: `https://api.collegefootballdata.com`
- Key stored as `CFBD_API_KEY` environment variable
- Rate limit: 1000 req/hour on free tier — batch weekly imports carefully

### VPS cron user
Run cron as the `bdailey` user (same as the service). Make sure
`/var/www/cfb-rankings/.env` or systemd environment has `CFBD_API_KEY` set.

---

**Epic Owner:** Bryan Dailey
**Related:** EPIC-029 (preseason setup), EPIC-019 (incremental updates), EPIC-034+ (see backlog)

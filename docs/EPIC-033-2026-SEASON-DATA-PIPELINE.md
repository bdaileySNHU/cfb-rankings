# EPIC-033: 2026 Season Data Pipeline

**Status:** 📋 To Do
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
- [ ] Run `import_games` utility (check `utilities/` for existing script or EPIC-019 tooling)
- [ ] Verify week assignments are correct (Week 1 = Aug 29–30)
- [ ] Confirm neutral site flags are set correctly (Kickoff Classic, etc.)
- [ ] Check that FCS opponents are marked correctly
- [ ] Verify game count matches CFBD (roughly 900 FBS regular season games)
- [ ] Commit any script changes needed to make the import idempotent

**Acceptance Criteria:**
- [ ] `SELECT COUNT(*) FROM games WHERE season=2026` returns ~900+
- [ ] Week 1 games present and dated correctly
- [ ] No duplicate games on re-run

---

### Story 33.2: Refresh 2026 Preseason Data
**Priority:** P0
**Effort:** 2–3 hours
**⏳ Blocked until late July / early August** — CFBD confirmed (May 4, 2026) that
recruiting rankings and returning production data for 2026 won't be published
until summertime. Attempting import now returns "No player data" for all teams.

Ensure recruiting rankings, transfer portal points, and returning production
percentages reflect the latest available 2026 data before ELO preseason ratings
are locked in.

**Tasks:**
- [ ] Re-run `utilities/import_player_data.py --year 2026` with latest CFBD data
- [ ] Verify 247Sports recruiting composite rankings loaded for 2026 class
- [ ] Verify transfer portal entries for 2026 are current
- [ ] Re-run preseason ELO calculation (`utilities/finalize_2026_preseason.sh`)
- [ ] Compare top-25 preseason ratings before/after — confirm changes are sensible
- [ ] Update `ranking_history` week-0 snapshots with recalculated values

**Acceptance Criteria:**
- [ ] Player data table has 2026 entries for all major programs
- [ ] Preseason ELO rankings updated and snapshot saved
- [ ] Top 5 teams are reasonable (Georgia, Ohio State, Texas, etc.)

---

### Story 33.3: Automated Weekly Import Cron Job ✅
**Priority:** P1
**Effort:** 3–4 hours
**Completed:** 2026-05-04 — `utilities/weekly_update.sh` created and cron entry
active (`0 9 * * 1`) on VPS. Logs to `/var/log/cfb-rankings/weekly.log`.

Set up a cron job on the VPS that runs every Monday morning to:
1. Fetch the previous week's game results from CFBD
2. Process them through the ELO algorithm
3. Update rankings
4. Restart the API service if needed

**Tasks:**
- [ ] Create `utilities/weekly_update.sh` (or Python equivalent) that:
  - Calls CFBD for results of the just-completed week
  - Inserts/updates scores in `Game` table
  - Runs ELO processing for those games
  - Saves a `ranking_history` snapshot for the week
  - Logs success/failure with timestamp
- [ ] Add cron entry on VPS: `0 9 * * 1 /var/www/cfb-rankings/utilities/weekly_update.sh >> /var/log/cfb-rankings/weekly.log 2>&1`
- [ ] Test the script manually against Week 1 results before going live
- [ ] Add log rotation for `/var/log/cfb-rankings/weekly.log`

**Acceptance Criteria:**
- [ ] Script runs end-to-end without manual intervention
- [ ] ELO ratings updated after a dry-run against known results
- [ ] Cron entry confirmed active (`crontab -l`)
- [ ] Log file created and readable

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

### Story 33.5: Season Runbook Documentation
**Priority:** P2
**Effort:** 1–2 hours

Write a clear, step-by-step runbook so the preseason → Week 1 transition and
each subsequent week's update is documented and repeatable.

**Tasks:**
- [ ] Create `docs/SEASON-RUNBOOK.md` covering:
  - Pre-season checklist (schedule import, player data, preseason ELO)
  - Week 1 activation steps (flip season to active, verify schedule)
  - Weekly update procedure (manual and automated)
  - End-of-season procedure (bowl games, CFP, final snapshot, archive)
  - Troubleshooting (missed week, bad data, rollback)
- [ ] Reference existing utility scripts with exact commands
- [ ] Note environment variables required (`CFBD_API_KEY`, `ADMIN_SECRET`)

**Acceptance Criteria:**
- [ ] A developer with no prior context can follow the runbook
- [ ] All commands tested and verified
- [ ] Covers at least pre-season, weekly, and end-of-season phases

---

## Technical Notes

### Existing tooling to reuse
- `utilities/import_player_data.py` — player/recruiting data from CFBD
- `utilities/finalize_2026_preseason.sh` — preseason ELO calculation
- `utilities/setup_2026_preseason.sh` — initial 2026 season setup
- `utilities/reprocess_season.py` — reprocess all games for a season
- EPIC-019 incremental update scripts (check `src/` for weekly import logic)

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

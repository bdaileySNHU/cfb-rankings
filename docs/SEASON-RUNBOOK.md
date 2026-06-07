# Season Runbook — Stat-urday College Football Rankings

A practical, command-focused reference for managing the data pipeline across the full
college football season lifecycle. All commands assume you are in `/var/www/cfb-rankings`
and the virtual environment is at `venv/`.

---

## 1. Pre-Season Checklist (late July / early August)

Run the following steps in order before the first game of the season.

### 1a. Backup the database

```bash
cp cfb_rankings.db cfb_rankings.db.backup_pre_season_$(date +%Y%m%d)
```

### 1b. Reprocess the previous season (fixes any ELO imbalances)

```bash
sudo -u www-data venv/bin/python3 utilities/reprocess_season.py --season 2025
```

### 1c. Archive the old season

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Season
db = SessionLocal()
s = db.query(Season).filter(Season.year == 2025).first()
if s:
    s.is_active = False
    db.commit()
    print("2025 archived")
db.close()
EOF
```

### 1d. Import player / recruiting data for the new year

Run imports for ~5 recruiting classes. Roster-based position strength (EPIC-039)
resolves each rostered player's rating by joining to these recruiting records, so
you need enough class depth that seniors (≈4 years back) still resolve a rating:

```bash
sudo -E -u www-data venv/bin/python3 utilities/import_player_data.py --year 2026
sudo -E -u www-data venv/bin/python3 utilities/import_player_data.py --year 2025
sudo -E -u www-data venv/bin/python3 utilities/import_player_data.py --year 2024
sudo -E -u www-data venv/bin/python3 utilities/import_player_data.py --year 2023
sudo -E -u www-data venv/bin/python3 utilities/import_player_data.py --year 2022
```

Add `--dry-run` first to estimate API usage. Add `--force` to skip the quota guard if
you have confirmed quota is available.

### 1d.2. Import current rosters (EPIC-039)

Snapshot each team's actual roster for the new season. Run this **after** the
recruiting import above so ratings resolve via the athlete-id join. This is what
makes position strength (and the team-page radar) reflect the real roster —
transfers in, departures out, all class years — rather than recruiting signings.

```bash
# One CFBD call per FBS team (~135). Writes the roster_players table.
sudo -E -u www-data venv/bin/python3 utilities/import_roster.py --year 2026
```

Notes:
- Requires the `roster_players` table — run `migrations/migrate_add_roster_table.py`
  once on first deploy (idempotent).
- The data source is controlled by `src/core/position_weights.json` →
  `"source": "roster"`. If a team has no roster snapshot, scoring falls back to
  recruiting-class data automatically, so this step is safe to skip in a pinch.
- Re-run after major roster churn (e.g. the spring/summer transfer-portal window)
  to keep the snapshot current before ratings are locked.

### 1d.3. Blend in on-field production (EPIC-040)

Fold prior-season production into each rostered player's quality score so
position strength reflects performance, not just recruiting pedigree. Run
**after** the roster import (1d.2). Covers QB/RB/WR/TE via PPA and DL/LB/DB via a
defensive box-score composite (tackles, TFL, sacks, passes defended, hurries).
OL has no per-player data and stays on recruiting pedigree.

```bash
# ~1 CFBD call (bulk PPA for the production year). Updates blended_rating.
sudo -E -u www-data venv/bin/python3 utilities/import_production.py --roster-season 2026
# Defaults: production-year = roster-season - 1 (2025); blend-weight from config.
```

Notes:
- Requires the production columns — run `migrations/migrate_add_roster_production.py`
  once on first deploy (idempotent).
- Controlled by `src/core/position_weights.json`: `"blend": true` and
  `"blend_weight"` (production share, default 0.5). Set `"blend": false` to score
  from recruiting pedigree only.
- Production is backward-looking: true freshmen / transfers without prior FBS
  snaps fall back to their recruiting score. OL always uses pedigree.
- One bulk PPA call + one bulk defensive-stats call (≈2 CFBD calls total).
- Defensive scores use a weighted box-score composite percentiled within each
  group — raw counts are snap-dependent, so it favors productive starters. See
  `docs/EPIC-040-PRODUCTION-BLENDED-RATINGS.md`.

### 1e. Create the new season and initialize preseason ratings

```bash
bash utilities/finalize_2026_preseason.sh
```

This script:
- Verifies player data exists in the DB
- Creates the 2026 season record (`scripts/start_new_season.py --season 2026`)
- Initializes ELO ratings for all FBS teams using position strength
- Saves a Week 0 (preseason) ranking snapshot to `ranking_history`
- Prints the top 15 for a quick sanity check

### 1f. Verify the top-25 looks reasonable

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.core.ranking_service import RankingService
db = SessionLocal()
rs = RankingService(db)
top = rs.get_current_rankings(2026, limit=25)
for r in top:
    print(f"  #{r['rank']:2} {r['team_name']:25} {r['elo_rating']:7.1f}")
db.close()
EOF
```

Expected: blue-blood programs (Georgia, Alabama, Ohio State, Michigan, etc.) near the
top. If a mid-major appears in the top 5, check that player data and transfer data
were imported correctly.

### 1g. Import the game schedule

```bash
sudo -u www-data venv/bin/python3 import_real_data.py --season 2026
```

This pulls all scheduled games (with 0-0 placeholder scores for future games) from the
CFBD API and inserts them into the `games` table.

### 1h. Restart the API service

```bash
sudo systemctl restart cfb-rankings
```

---

## 2. Week 1 Activation

Run these checks the week before the first game.

### Confirm the season is marked active in the DB

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Season
db = SessionLocal()
s = db.query(Season).filter(Season.is_active == True).first()
print(f"Active season: {s.year if s else 'NONE'}, current_week={s.current_week if s else 'N/A'}")
db.close()
EOF
```

### Verify Week 1 games are in the schedule

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Game
db = SessionLocal()
games = db.query(Game).filter(Game.season == 2026, Game.week == 1).all()
print(f"Week 1 games scheduled: {len(games)}")
for g in games[:5]:
    print(f"  {g.id}: home={g.home_team_id} vs away={g.away_team_id}")
db.close()
EOF
```

Expect 50–70 games for Week 1 of a full FBS schedule.

### Check that predictions are generating

```bash
curl -s http://localhost:8000/api/predictions?season=2026 | python3 -m json.tool | head -40
```

If predictions return an empty list, confirm games are in the DB and the season is active.

---

## 3. Weekly Update (every Monday after games)

### Automated cron (runs at 9 AM every Monday)

```
0 9 * * 1 /var/www/cfb-rankings/utilities/weekly_update.sh >> /var/log/cfb-rankings/weekly.log 2>&1
```

The script:
1. Loads `CFBD_API_KEY` from `.env` if not already set
2. Detects the active season from the DB
3. Runs `import_real_data.py --season <SEASON>` to pull latest scores
4. Processes all unprocessed games with scores through the ELO algorithm
5. Saves `ranking_history` snapshots for each newly completed week
6. Restarts the `cfb-rankings` service

### Run the weekly update manually (if cron fails or needs re-running)

```bash
cd /var/www/cfb-rankings
export CFBD_API_KEY=<your-key>
bash utilities/weekly_update.sh
```

### Check the weekly log

```bash
tail -50 /var/log/cfb-rankings/weekly.log
```

Look for lines starting with `✓` (success) and `✗` (failure). A successful run ends with:

```
  Weekly update complete — YYYY-MM-DD HH:MM:SS
```

### Verify ELO updated after the run

Check the rankings page in the browser, or query the DB directly:

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.core.ranking_service import RankingService
db = SessionLocal()
rs = RankingService(db)
top = rs.get_current_rankings(2026, limit=5)
for r in top:
    print(f"  #{r['rank']:2} {r['team_name']:25} {r['elo_rating']:7.1f}  W{r['wins']}-L{r['losses']}")
db.close()
EOF
```

Or via the API:

```bash
curl -s http://localhost:8000/api/rankings?season=2026 | python3 -m json.tool | head -50
```

---

## 4. Mid-Season Manual Import

Use this when the cron missed a week, scores were wrong, or you need to re-process a
specific week without running the full pipeline.

### Re-run import for a specific week (command line)

```bash
cd /var/www/cfb-rankings
export CFBD_API_KEY=<your-key>
sudo -u www-data venv/bin/python3 import_real_data.py --season 2026 --max-week 8
```

To reprocess from scratch for a week (reset and re-run ELO):

```bash
sudo -u www-data venv/bin/python3 utilities/fix_unprocessed_games.py
```

### Use the Admin API endpoints (Story 33.4)

**Check last import status:**

```bash
curl -s -H "X-Admin-Key: $ADMIN_SECRET" \
  http://localhost:8000/api/admin/import/status | python3 -m json.tool
```

**Trigger a new import for the whole season:**

```bash
curl -s -X POST -H "X-Admin-Key: $ADMIN_SECRET" \
  "http://localhost:8000/api/admin/import/results?season=2026" | python3 -m json.tool
```

**Trigger import for a specific week:**

```bash
curl -s -X POST -H "X-Admin-Key: $ADMIN_SECRET" \
  "http://localhost:8000/api/admin/import/results?season=2026&week=8" | python3 -m json.tool
```

### Manually set the current week (if detection is wrong)

```bash
curl -s -X POST \
  "http://localhost:8000/api/admin/update-current-week?year=2026&week=8"
```

---

## 5. End of Season (December–January)

### 5a. Import bowl games

Bowl games use a separate postseason import path inside `import_real_data.py`
(`import_bowl_games` function). Run the full import with postseason flag:

```bash
cd /var/www/cfb-rankings
export CFBD_API_KEY=<your-key>
sudo -u www-data venv/bin/python3 import_real_data.py --season 2026
```

After bowl games are in the DB, re-run the ELO step via `weekly_update.sh` or
manually process unprocessed games:

```bash
bash utilities/weekly_update.sh
```

### 5b. CFP / Playoff import

Playoff games are fetched as part of `import_real_data.py` postseason run. The same
`weekly_update.sh` call handles processing.

Check that playoff weeks (16–19) are reflected in rankings:

```bash
curl -s "http://localhost:8000/api/games?season=2026&processed=true" | \
  python3 -m json.tool | grep '"week"' | sort -u
```

### 5c. Save the final season snapshot

```bash
sudo -u www-data venv/bin/python3 utilities/save_final_season_snapshot.py
```

### 5d. Validate the season data

```bash
sudo -u www-data venv/bin/python3 utilities/validate_season.py --season 2026 \
  --output docs/season-2026-validation-report.md
```

### 5e. Generate season summary stats

```bash
sudo -u www-data venv/bin/python3 utilities/finalize_season_stats.py --season 2026 \
  --output docs/season-2026-summary.md
```

### 5f. Archive the season (dry-run first, then confirm)

```bash
# Dry-run — shows what would be archived
sudo -u www-data venv/bin/python3 utilities/archive_season.py --season 2026

# Actually archive
sudo -u www-data venv/bin/python3 utilities/archive_season.py --season 2026 --confirm
```

### 5g. Mark the season inactive

The `archive_season.py --confirm` step sets `is_active = False` automatically.
Verify with:

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Season
db = SessionLocal()
for s in db.query(Season).order_by(Season.year.desc()).all():
    status = "ACTIVE" if s.is_active else "archived"
    print(f"  {s.year}: {status}")
db.close()
EOF
```

---

## 6. New Season Setup

When ready to set up the next season (typically late July):

1. Follow Section 1 (Pre-Season Checklist) for the new year.
2. Bump the year in all commands from the old season to the new one.
3. The full setup flow is documented in EPIC-033. Key scripts:
   - `bash utilities/setup_2026_preseason.sh` — backup, reprocess prior season, archive old
   - `bash utilities/finalize_2026_preseason.sh` — create season, init ratings, save Week 0

For a new season beyond 2026, copy and adapt those scripts with the new year.

---

## 7. Environment Variables Reference

All variables should be set in `/var/www/cfb-rankings/.env` or as `Environment=` lines
in `deploy/cfb-rankings.service`.

| Variable | Required | Description |
|---|---|---|
| `CFBD_API_KEY` | Yes | CollegeFootballData.com API key. Get one at https://collegefootballdata.com/key |
| `ADMIN_SECRET` | Yes | Secret key for admin-protected API endpoints (`X-Admin-Key` header). Set to a long random string. |
| `DATABASE_URL` | No | SQLAlchemy database URL. Default: `sqlite:///./cfb_rankings.db` |
| `CFBD_MONTHLY_LIMIT` | No | Monthly API call budget. Default: `30000` |
| `CFB_SEASON_END_DATE` | No | When the CFB season ends in `MM-DD` format. Default: `02-01` (February 1). Affects season-year detection. |

**Systemd service example** (`deploy/cfb-rankings.service`):

```ini
Environment="CFBD_API_KEY=your-key-here"
Environment="DATABASE_URL=sqlite:///./cfb_rankings.db"
Environment="ADMIN_SECRET=your-admin-secret-here"
```

After editing the service file:

```bash
sudo systemctl daemon-reload
sudo systemctl restart cfb-rankings
```

---

## 8. Troubleshooting

### Service won't start

```bash
journalctl -u cfb-rankings -n 50
```

Common causes:
- Missing `CFBD_API_KEY` in the service environment
- Python virtual environment not found at `venv/bin/gunicorn`
- Port 8000 already in use (check `ss -tlnp | grep 8000`)
- Database file permissions (`chown www-data:www-data cfb_rankings.db`)

### Import fails

```bash
tail -100 /var/log/cfb-rankings/weekly.log
```

Common causes:
- `CFBD_API_KEY` not set or revoked — verify at https://collegefootballdata.com/key
- Monthly quota exceeded — check `curl http://localhost:8000/api/admin/api-usage`
- Network timeout — retry the import; CFBD API has retry logic built in

### Rankings not updating after import

Check whether games were actually marked `is_processed`:

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Game
db = SessionLocal()
total = db.query(Game).filter(Game.season == 2026).count()
processed = db.query(Game).filter(Game.season == 2026, Game.is_processed == True).count()
unprocessed_with_scores = db.query(Game).filter(
    Game.season == 2026,
    Game.is_processed == False,
    Game.home_score != 0,
    Game.away_score != 0,
).count()
print(f"Total: {total}, Processed: {processed}, Unprocessed with scores: {unprocessed_with_scores}")
db.close()
EOF
```

If `unprocessed_with_scores > 0`, run:

```bash
bash utilities/weekly_update.sh
```

Or use `utilities/fix_unprocessed_games.py` for targeted fixes.

### Wrong scores / need to reprocess a week

1. Mark the affected games as unprocessed so ELO reruns them:

```bash
sudo -u www-data venv/bin/python3 - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Game
db = SessionLocal()
# Replace 8 with the week to reset
games = db.query(Game).filter(Game.season == 2026, Game.week == 8).all()
for g in games:
    g.is_processed = False
    g.home_rating_change = 0.0
    g.away_rating_change = 0.0
db.commit()
print(f"Reset {len(games)} games in Week 8")
db.close()
EOF
```

2. Re-import scores and reprocess:

```bash
export CFBD_API_KEY=<your-key>
sudo -u www-data venv/bin/python3 import_real_data.py --season 2026
bash utilities/weekly_update.sh
```

3. Or use the admin API endpoint:

```bash
curl -s -X POST -H "X-Admin-Key: $ADMIN_SECRET" \
  "http://localhost:8000/api/admin/import/results?season=2026&week=8" | python3 -m json.tool
```

### Recalculate all rankings from scratch

```bash
curl -s -X POST "http://localhost:8000/api/calculate?season=2026" | python3 -m json.tool
```

This resets all team ratings to preseason values and reprocesses every game in
chronological order.

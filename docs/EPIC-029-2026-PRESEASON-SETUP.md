# EPIC-029: 2026 Preseason Setup with Position Strength

**Status:** 🚧 In Progress (Stories 29.1, 29.2, and 29.4 partial complete)
**Priority:** High
**Created:** 2026-05-01
**Target Release:** Before 2026 Season Kickoff

---

## Problem Statement

The system is between the 2025 and 2026 seasons with several unresolved data issues that must be fixed before 2026 preseason ratings can be accurately calculated:

1. **2025 season incomplete** — 140 games have final scores but were never processed through the ELO algorithm (weekly updates stopped at Week 14). End-of-season team ratings are inaccurate.
2. **Two active seasons** — Both 2024 and 2025 are marked `is_active=True`. 2024 should be archived.
3. **No player data** — The `players` table exists but is empty. Position strength bonus cannot be applied without recruiting data.
4. **Feature flag disabled** — The position strength bonus built in EPIC-PRESEASON-2026-01 has never been enabled in production.
5. **No 2026 season** — The database has no 2026 season record, so preseason ratings cannot be initialized.

### Impact

- 2025 final ELO standings are wrong (missing ~140 late-season/bowl/playoff results)
- 2026 preseason ratings will be inaccurate without position strength data
- The position strength work (73 tests, full implementation) is sitting unused

---

## Goals

1. Produce accurate end-of-2025 ELO ratings by fully processing the 2025 season
2. Clean up season management (archive 2024, confirm 2025 final)
3. Populate the players table with 4-5 years of recruiting class data
4. Enable the position strength feature for 2026 preseason ratings
5. Initialize all 2026 preseason ratings with the full formula:
   `base + recruiting_bonus + transfer_bonus + returning_bonus + position_strength_bonus`

---

## Stories

### Story 29.1: Finalize the 2025 Season
**Priority:** P0
**Effort:** ~15 minutes
**Status:** ⬜ To Do

**Problem:** 140 games with final scores were never processed through ELO. The weekly update loop ran through Week 14 but bowl games and CFP games (Weeks 15–17) were imported but not processed.

**Tasks:**
- [x] Backup the database before making changes
- [x] Run `reprocess_season.py --season 2025` to reset and replay all 2025 games in order
- [x] Verify all 895 games are processed (`is_processed=True`)
- [x] Confirm season current_week reflects full season completion
- [x] Spot-check: verify CFP champion has correct final ELO

**Command:**
```bash
# Backup first
cp docs/cfb_rankings.db docs/cfb_rankings.db.backup_pre_29.1

# Dry run to preview
arch -x86_64 /usr/local/bin/python3.11 utilities/reprocess_season.py --season 2025 --dry-run

# Full reprocess
arch -x86_64 /usr/local/bin/python3.11 utilities/reprocess_season.py --season 2025
```

**Acceptance Criteria:**
- All 895 2025 games show `is_processed=True`
- Zero games with scores remaining unprocessed
- Top teams in final ELO reflect 2025 season results

---

### Story 29.2: Archive 2024 Season
**Priority:** P1
**Effort:** ~5 minutes
**Status:** ⬜ To Do

**Problem:** Both 2024 and 2025 are marked `is_active=True`. Only the most recently completed season should be active until 2026 begins.

**Tasks:**
- [x] Set `Season(year=2024).is_active = False`
- [x] Confirm `Season(year=2025).is_active = True`
- [x] Verify `/api/rankings` returns 2025 data by default

**Command:**
```bash
arch -x86_64 /usr/local/bin/python3.11 -c "
from src.models.database import SessionLocal
from src.models.models import Season
db = SessionLocal()
s2024 = db.query(Season).filter(Season.year==2024).first()
s2024.is_active = False
db.commit()
print('2024 archived. Active seasons:')
for s in db.query(Season).filter(Season.is_active==True).all():
    print(f'  {s.year}: week={s.current_week}')
db.close()
"
```

**Acceptance Criteria:**
- Only 2025 is active
- `/api/rankings` defaults to 2025 data

---

### Story 29.3: Import Player Recruiting Data (2022–2026)
**Priority:** P0
**Effort:** 2–3 hours (API rate-limited)
**Status:** ⬜ To Do

**Problem:** The players table is empty. Position strength bonus requires recruiting rating data for each team's roster, which spans multiple recruiting classes.

**Why 5 years:** A typical FBS roster contains players from the last 4–5 recruiting classes (freshmen through 5th-year seniors). Importing 2022–2026 gives full coverage.

**Estimated API usage:** ~133 calls/year × 5 years = ~665 calls total

**Tasks:**
- [ ] Verify `CFBD_API_KEY` is set in the shell
- [ ] Check API quota before starting
- [ ] Import each year sequentially (2022 → 2023 → 2024 → 2025 → 2026)
- [ ] Verify player counts per year after each import
- [ ] Confirm at least one well-known team has expected players (e.g., Georgia QB recruiting)

**Commands (run in a terminal with CFBD_API_KEY set):**
```bash
# Check quota first
arch -x86_64 /usr/local/bin/python3.11 utilities/import_player_data.py --year 2026 --dry-run

# Import each year (allow 30-40 min per year)
arch -x86_64 /usr/local/bin/python3.11 utilities/import_player_data.py --year 2022
arch -x86_64 /usr/local/bin/python3.11 utilities/import_player_data.py --year 2023
arch -x86_64 /usr/local/bin/python3.11 utilities/import_player_data.py --year 2024
arch -x86_64 /usr/local/bin/python3.11 utilities/import_player_data.py --year 2025
arch -x86_64 /usr/local/bin/python3.11 utilities/import_player_data.py --year 2026
```

**Verification:**
```bash
arch -x86_64 /usr/local/bin/python3.11 -c "
from src.models.database import SessionLocal
from src.models.models import Player
from sqlalchemy import func
db = SessionLocal()
rows = db.execute(__import__('sqlalchemy').text(
    'SELECT recruiting_year, COUNT(*) FROM players GROUP BY recruiting_year ORDER BY recruiting_year'
)).fetchall()
for year, count in rows:
    print(f'  {year}: {count} players')
print(f'  Total: {db.query(Player).count()}')
db.close()
"
```

**Acceptance Criteria:**
- Players table has data for all 5 years (2022–2026)
- At least 100 teams have players in each year
- No import errors for major programs (Alabama, Georgia, Ohio State, etc.)

---

### Story 29.4: Create 2026 Season and Enable Position Strength
**Priority:** P0
**Effort:** ~10 minutes
**Status:** ⬜ To Do

**Tasks:**
- [ ] Enable position strength feature flag in `src/core/position_weights.json`
- [ ] Create 2026 season record (`start_new_season.py --season 2026`)
- [ ] Initialize 2026 preseason ratings for all teams
- [ ] Save Week 0 rankings to `ranking_history` for the 2026 season
- [ ] Verify top teams are in expected order (Alabama, Georgia, Ohio State, etc. near top)

**Step 1 — Enable feature flag** ✅ Done (2026-05-01):
```json
// src/core/position_weights.json
{
  "enabled": true,
  ...
}
```

**Step 2 — Create 2026 season:**
```bash
arch -x86_64 /usr/local/bin/python3.11 scripts/start_new_season.py --season 2026
```

**Step 3 — Initialize preseason ratings:**
```bash
arch -x86_64 /usr/local/bin/python3.11 -c "
from src.models.database import SessionLocal
from src.models.models import Team
from src.core.ranking_service import RankingService
db = SessionLocal()
rs = RankingService(db)
teams = db.query(Team).filter(Team.is_fcs == False).all()
print(f'Initializing preseason ratings for {len(teams)} FBS teams...')
for team in teams:
    rs.initialize_team_rating(team)
db.commit()
print('Done. Saving Week 0 rankings...')
rs.save_weekly_rankings(season=2026, week=0)
db.commit()
print('Complete.')
db.close()
"
```

**Step 4 — Spot-check:**
```bash
arch -x86_64 /usr/local/bin/python3.11 -c "
from src.models.database import SessionLocal
from src.core.ranking_service import RankingService
from src.models.models import Season
db = SessionLocal()
rs = RankingService(db)
# Temporarily make 2026 queryable
from src.models.models import Season
s = db.query(Season).filter(Season.year==2026).first()
print(f'2026 season: week={s.current_week}')
top = rs.get_current_rankings(2026, limit=10)
for r in top:
    print(f'  #{r[\"rank\"]} {r[\"team_name\"]}: {r[\"elo_rating\"]}')
db.close()
"
```

**Acceptance Criteria:**
- 2026 season exists with `current_week=0`
- All FBS teams have `initial_rating > 0` for 2026
- Position strength bonus is reflected in ratings (teams with elite QB recruiting rated higher)
- Week 0 rankings saved to `ranking_history`

---

## Technical Notes

### Position Strength Formula (when enabled)
```
preseason_rating = base                   # 1500 FBS / 1300 FCS
                 + recruiting_bonus       # 0–200 pts (rank 1–50+)
                 + transfer_bonus         # 0–100 pts (rank 1–50+)
                 + returning_bonus        # 0–40 pts (production %)
                 + position_strength_bonus # 0–150 pts (player ratings)
```

### Weight Rationale (position_weights.json)
| Position | Weight | Rationale |
|----------|--------|-----------|
| QB | 30% | Most impactful position |
| OL | 25% | Games won in the trenches |
| DL | 20% | Defensive line drives outcomes |
| DB | 15% | Critical in modern passing game |
| LB | 5% | Important but less decisive |
| RB/WR | 2.5% each | Scheme-dependent |
| TE/ST | 0% | Deferred for now |

### Rollback
If results look wrong after enabling:
```bash
# Disable feature flag
# Edit src/core/position_weights.json: "enabled": false
# Re-run Step 3 (initialize ratings) — bonus drops to 0.0
```

---

## Success Metrics

- [ ] 2025 season: all 895 games processed
- [ ] 2024 season: archived (is_active=False)
- [ ] Players table: 5 years of data, all major programs covered
- [ ] 2026 preseason ratings: position strength bonus applied
- [ ] Top 10 preseason rankings: intuitively correct (recruiting blue-bloods near top)
- [ ] All existing tests still pass after changes

---

## Future Work (Post-29)

After this epic, consider:
- **Frontend display** — Show position strength breakdown on team pages
- **Weight tuning** — Correlate position strength scores with end-of-season ELO to optimize weights
- **Radar charts** — Visualize position group strengths per team
- **Transfer portal integration** — Recalculate position strength when portal data is refreshed

---

**Epic Owner:** Bryan Dailey
**Related:** EPIC-PRESEASON-2026-01 (built the feature), EPIC-026 (transfer portal rankings)

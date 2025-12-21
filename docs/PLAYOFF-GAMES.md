# College Football Playoff Game Handling

This document describes how the system handles College Football Playoff (CFP) games, including automatic import, week assignment, and ranking calculations.

---

## Overview

The system automatically imports and processes playoff games from the CollegeFootballData.com (CFBD) API. Playoff games are:

- **Automatically imported** during regular data imports
- **Assigned to weeks 16-19** (separate from regular season weeks 0-15)
- **Categorized by playoff round** (First Round, Quarterfinals, Semifinals, Championship)
- **Included in ELO rankings** once scores are available

---

## Playoff Format (2024+)

The 12-team College Football Playoff format includes:

| Round | Week | Number of Games | Example |
|-------|------|----------------|---------|
| **First Round** | 16 | 4 games | Home team hosting games on campus |
| **Quarterfinals** | 17 | 4 games | New Year's Six bowl games |
| **Semifinals** | 18 | 2 games | Major bowl games |
| **National Championship** | 19 | 1 game | National title game |

**Total:** 11 playoff games per season

---

## How Playoff Games Are Imported

### Automatic Import

Playoff games are automatically imported when you run:

```bash
python3 import_real_data.py
```

The `import_playoff_games()` function:
1. Fetches postseason games from CFBD API with `season_type="postseason"`
2. Filters for playoff games by keywords ("playoff", "semifinal", "quarterfinal", "first round", "CFP")
3. Assigns week numbers based on playoff round
4. Creates game records with `game_type='playoff'` and `postseason_name` (e.g., "CFP First Round")

### Week Assignment Logic

```python
if "national championship" in notes:
    week = 19  # Championship game
elif "semifinal" in notes:
    week = 18  # Semifinal games
elif "quarterfinal" in notes:
    week = 17  # Quarterfinal games
elif "first round" in notes:
    week = 16  # First-round games
```

### Game Classification

Playoff games are stored with:
- `game_type = 'playoff'`
- `postseason_name = 'CFP First Round'` (or appropriate round)
- `week = 16-19` (depending on round)
- `is_neutral_site = True` (playoff games are typically neutral site)

---

## Scheduled vs Completed Games

### Scheduled Games (Future)

Games that haven't been played yet (e.g., quarterfinals before first-round completes):

- **Imported with 0-0 scores**
- **Marked as `excluded_from_rankings = True`**
- **Predictions are NOT generated** (because matchups may not be determined)

Example: Quarterfinal games imported before first-round games are played

### Completed Games

Once games have final scores:

- **Scores updated from CFBD API**
- **`excluded_from_rankings` set to `False`**
- **Processed for ELO calculations** (winners gain ELO, losers lose ELO)
- **Quarter scores imported** (if available)

---

## Manual Playoff Game Import

If you need to manually import playoff games for a specific season:

```bash
cd /var/www/cfb-rankings
source venv/bin/activate

# Import playoff games for current season
python3 -c "
from import_real_data import import_playoff_games
from src.integrations.cfbd_client import CFBDClient
from src.models.database import SessionLocal
from src.core.ranking_service import RankingService

db = SessionLocal()
cfbd = CFBDClient()
ranking_service = RankingService(db)

# Assuming team_objects dict is available or load teams first
from src.models.models import Team
teams = db.query(Team).all()
team_objects = {team.name: team for team in teams}

# Import playoff games
count = import_playoff_games(cfbd, db, team_objects, 2025, ranking_service)
print(f'Imported {count} playoff games')

db.close()
"
```

---

## Verifying Playoff Games

### Check Playoff Games in Database

```bash
# SSH into server
ssh your-username@cfb.bdailey.com
cd /var/www/cfb-rankings

# Query playoff games for current season
sqlite3 cfb_rankings.db "
SELECT
  week,
  postseason_name,
  home_team.name || ' ' || home_score || '-' || away_score || ' ' || away_team.name as matchup,
  is_processed,
  excluded_from_rankings
FROM games
JOIN teams as home_team ON games.home_team_id = home_team.id
JOIN teams as away_team ON games.away_team_id = away_team.id
WHERE games.season = 2025
  AND games.game_type = 'playoff'
ORDER BY week, postseason_name;
"
```

**Expected Output:**

```
16|CFP First Round|Oklahoma 24-34 Alabama|1|0
16|CFP First Round|Texas A&M 3-10 Miami|1|0
16|CFP First Round|Tulane 10-41 Ole Miss|1|0
16|CFP First Round|James Madison 34-51 Oregon|1|0
17|CFP Quarterfinal|TBD 0-0 TBD|0|1
17|CFP Quarterfinal|TBD 0-0 TBD|0|1
...
```

### Check Playoff Game Count

```bash
sqlite3 cfb_rankings.db "
SELECT
  week,
  COUNT(*) as game_count,
  SUM(CASE WHEN is_processed = 1 THEN 1 ELSE 0 END) as processed,
  SUM(CASE WHEN excluded_from_rankings = 1 THEN 1 ELSE 0 END) as excluded
FROM games
WHERE season = 2025 AND game_type = 'playoff'
GROUP BY week
ORDER BY week;
"
```

---

## Week Validation

The system validates week numbers from **0 to 19**:

- **Week 0:** Preseason games
- **Weeks 1-15:** Regular season (includes conference championships)
- **Weeks 16-19:** Playoff games

All import and update scripts enforce this validation. Invalid week numbers will be rejected.

---

## Weekly Update Script

The `weekly_update.py` script automatically handles playoff games:

1. Checks if we're in active season (August-January)
2. Runs `import_real_data.py` which includes playoff import
3. Updates scores for completed playoff games
4. Processes new playoff games for ELO rankings

**No manual intervention needed** - playoff games are handled automatically!

---

## API Response

Playoff games are returned by the API with the `game_type` field:

```bash
# Query API for playoff games
curl https://cfb.bdailey.com/api/games?season=2025&game_type=playoff | python3 -m json.tool
```

**Response includes:**
- `game_type`: "playoff"
- `postseason_name`: "CFP First Round", "CFP Quarterfinal", etc.
- `week`: 16-19
- `is_processed`: true/false (whether ELO has been calculated)
- `excluded_from_rankings`: true/false (scheduled games are excluded)

---

## Troubleshooting

### Issue 1: Playoff Games Not Imported

**Symptoms:**
- Database shows 0 playoff games
- API returns empty list for playoff games

**Fix:**

```bash
cd /var/www/cfb-rankings
source venv/bin/activate

# Run full import to fetch playoff games
python3 import_real_data.py --season 2025

# Check if playoff games now exist
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE season = 2025 AND game_type = 'playoff';"
```

### Issue 2: Scheduled Games Affecting Rankings

**Symptoms:**
- Games with 0-0 scores appearing in rankings
- ELO calculations failing on unplayed games

**Fix:**

```bash
# Mark scheduled playoff games as excluded
sqlite3 cfb_rankings.db "
UPDATE games
SET excluded_from_rankings = 1
WHERE game_type = 'playoff'
  AND home_score = 0
  AND away_score = 0
  AND season = 2025;
"

# Restart backend
sudo systemctl restart cfb-rankings
```

### Issue 3: Playoff Games Not Processed

**Symptoms:**
- Playoff games have scores but `is_processed = 0`
- ELO ratings not updated after playoff games

**Fix:**

```bash
cd /var/www/cfb-rankings
source venv/bin/activate

# Process unprocessed playoff games
python3 -c "
from src.models.database import SessionLocal
from src.models.models import Game
from src.core.ranking_service import RankingService

db = SessionLocal()
ranking_service = RankingService(db)

# Find unprocessed playoff games with scores
games = db.query(Game).filter(
    Game.game_type == 'playoff',
    Game.is_processed == False,
    Game.home_score > 0  # Has actual scores
).all()

for game in games:
    print(f'Processing: {game.away_team.name} @ {game.home_team.name}')
    result = ranking_service.process_game(game)
    print(f'  Winner: {result[\"winner_name\"]}')

db.close()
"

deactivate
```

### Issue 4: Invalid Week Number Error

**Symptoms:**
- Error: "Week 17 exceeds maximum 15"
- Playoff games rejected during import

**Fix:**

The system has been updated to support weeks 0-19. If you see this error:

1. Update `weekly_update.py` to allow weeks 0-19
2. Update `ranking_service.py` validation
3. Update `api/main.py` validation

All validation should use `MAX_WEEK = 19`.

---

## Best Practices

### 1. Import Playoff Games After Selection Sunday

Run a full import after the playoff bracket is announced (around Week 15):

```bash
python3 import_real_data.py --season 2025 --max-week 19
```

This will import all playoff games, including future games with TBD matchups.

### 2. Update After Each Playoff Round

Run weekly updates after each playoff round completes:

```bash
# After first-round games (Week 16)
python3 import_real_data.py

# After quarterfinals (Week 17)
python3 import_real_data.py

# After semifinals (Week 18)
python3 import_real_data.py

# After championship (Week 19)
python3 import_real_data.py
```

### 3. Verify Rankings After Playoff Games

Check that playoff games updated ELO ratings correctly:

```bash
sqlite3 cfb_rankings.db "
SELECT
  name,
  elo_rating,
  wins,
  losses
FROM teams
WHERE name IN ('Georgia', 'Alabama', 'Ohio State', 'Michigan')
ORDER BY elo_rating DESC;
"
```

---

## Summary

**Playoff games are handled automatically!**

The system:
- ✅ Imports playoff games from CFBD API
- ✅ Assigns playoff games to weeks 16-19
- ✅ Excludes scheduled games from rankings
- ✅ Processes completed games for ELO calculations
- ✅ Updates playoff game scores automatically

**No manual intervention needed** - just run your regular weekly updates and playoff games will be handled correctly.

---

## Related Documentation

- [UPDATE-GAME-DATA.md](UPDATE-GAME-DATA.md) - How to update game data weekly
- [WEEKLY-WORKFLOW.md](WEEKLY-WORKFLOW.md) - Weekly update workflow
- [EPIC-023-BOWL-GAMES-PLAYOFFS.md](EPIC-023-BOWL-GAMES-PLAYOFFS.md) - Technical implementation details

---

**Questions?** Check the logs:
```bash
sudo journalctl -u cfb-rankings -f
```

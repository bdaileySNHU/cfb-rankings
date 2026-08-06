#!/bin/bash
# EPIC-029 Story 29.4 / EPIC-033 Story 33.2: Initialize preseason ratings.
# Run after the player, roster, and production imports are complete.
#
# Usage:
#   bash utilities/finalize_2026_preseason.sh            # 2026 on the VPS
#   bash utilities/finalize_2026_preseason.sh 2027       # a later season
#
# Env overrides (for local rehearsal against a scratch DB):
#   CFB_ROOT=. CFB_PYTHON=python3 DATABASE_URL=sqlite:///rehearsal.db \
#     bash utilities/finalize_2026_preseason.sh 2026

set -e
export SEASON="${1:-2026}"
PYTHON="${CFB_PYTHON:-sudo -u www-data venv/bin/python}"
cd "${CFB_ROOT:-/var/www/cfb-rankings}"

echo "============================================================"
echo "Initialize $SEASON Preseason Ratings"
echo "============================================================"
echo ""

# Verify player data exists
echo "[Check] Verifying player data..."
$PYTHON - <<'EOF'
import os
from src.models.database import SessionLocal
from src.models.models import Player
from sqlalchemy import text

season = int(os.environ["SEASON"])
db = SessionLocal()
total = db.query(Player).count()
print(f"  Total players in DB: {total}")
if total == 0:
    print("  ✗ ERROR: No player data found. Run the import first.")
    exit(1)
rows = db.execute(text("SELECT recruiting_year, COUNT(*) FROM players GROUP BY recruiting_year ORDER BY recruiting_year")).fetchall()
for year, count in rows:
    print(f"  {year}: {count} players")
if not any(year == season for year, _ in rows):
    print(f"  ✗ ERROR: No {season} recruiting class. Run import_player_data.py --year {season} first.")
    exit(1)
db.close()
EOF
echo ""

# Create the season only if it does not already exist — start_new_season.py
# exits non-zero on "Season already exists", which under `set -e` would abort
# the re-rating below.
echo "[Step 4a] Ensuring $SEASON season exists..."
if $PYTHON - <<'EOF'
import os, sys
from src.models.database import SessionLocal
from src.models.models import Season

db = SessionLocal()
exists = db.query(Season).filter(Season.year == int(os.environ["SEASON"])).first() is not None
db.close()
sys.exit(0 if exists else 1)
EOF
then
    echo "  Season $SEASON already exists — skipping creation"
else
    $PYTHON scripts/start_new_season.py --season "$SEASON"
fi
echo ""

# Initialize preseason ratings with position strength
echo "[Step 4b] Initializing $SEASON preseason ratings (position strength enabled)..."
$PYTHON - <<'EOF'
import os
from src.models.database import SessionLocal
from src.models.models import Season, Team
from src.core.ranking_service import RankingService

season = int(os.environ["SEASON"])
db = SessionLocal()
rs = RankingService(db)
teams = db.query(Team).filter(Team.is_fcs == False).all()
print(f"  Initializing ratings for {len(teams)} FBS teams...")

# season= is required: it drives previous-season regression (EPIC-030) and the
# season-aware position-strength bonus. Omitting it silently rates off defaults.
for team in teams:
    rs.initialize_team_rating(team, season=season)

db.commit()
print("  ✓ Ratings initialized")

# Refresh week 0 AND the season's current_week. get_current_rankings() serves
# current_week, so a stale snapshot there hides the new ratings from the API.
current_week = db.query(Season).filter(Season.year == season).first().current_week
for week in sorted({0, current_week}):
    rs.save_weekly_rankings(season=season, week=week)
    print(f"  ✓ Week {week} rankings saved")
db.commit()
db.close()
EOF
echo ""

# Show top 15
echo "[Check] $SEASON Preseason Top 15:"
$PYTHON - <<'EOF'
import os
from src.models.database import SessionLocal
from src.core.ranking_service import RankingService

db = SessionLocal()
rs = RankingService(db)
for r in rs.get_current_rankings(int(os.environ["SEASON"]), limit=15):
    print(f"  #{r['rank']:2} {r['team_name']:25} {r['elo_rating']:7.1f}")
db.close()
EOF

echo ""
echo "============================================================"
echo "$SEASON preseason ratings are initialized."
echo "Restart the API to serve new ratings:"
echo "  sudo systemctl restart cfb-rankings"
echo "============================================================"

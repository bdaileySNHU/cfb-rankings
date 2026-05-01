#!/bin/bash
# EPIC-029 Story 29.4: Create 2026 Season and Initialize Preseason Ratings
# Run this on the VPS after player data import is complete
# Usage: bash utilities/finalize_2026_preseason.sh

set -e
PYTHON="sudo -u www-data venv/bin/python"
cd /var/www/cfb-rankings

echo "============================================================"
echo "EPIC-029 Story 29.4: Initialize 2026 Preseason Ratings"
echo "============================================================"
echo ""

# Verify player data exists
echo "[Check] Verifying player data..."
$PYTHON - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Player
from sqlalchemy import text
db = SessionLocal()
total = db.query(Player).count()
print(f"  Total players in DB: {total}")
if total == 0:
    print("  ✗ ERROR: No player data found. Run the import first.")
    exit(1)
rows = db.execute(text("SELECT recruiting_year, COUNT(*) FROM players GROUP BY recruiting_year ORDER BY recruiting_year")).fetchall()
for year, count in rows:
    print(f"  {year}: {count} players")
db.close()
EOF
echo ""

# Create 2026 season
echo "[Step 4a] Creating 2026 season..."
$PYTHON scripts/start_new_season.py --season 2026
echo ""

# Initialize preseason ratings with position strength
echo "[Step 4b] Initializing 2026 preseason ratings (position strength enabled)..."
$PYTHON - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Team
from src.core.ranking_service import RankingService

db = SessionLocal()
rs = RankingService(db)
teams = db.query(Team).filter(Team.is_fcs == False).all()
print(f"  Initializing ratings for {len(teams)} FBS teams...")

for team in teams:
    rs.initialize_team_rating(team)

db.commit()
print("  ✓ Ratings initialized")

# Save Week 0 rankings snapshot
print("  Saving Week 0 rankings to history...")
rs.save_weekly_rankings(season=2026, week=0)
db.commit()
print("  ✓ Week 0 rankings saved")
db.close()
EOF
echo ""

# Show top 15
echo "[Check] 2026 Preseason Top 15:"
$PYTHON - <<'EOF'
from src.models.database import SessionLocal
from src.core.ranking_service import RankingService
db = SessionLocal()
rs = RankingService(db)
top = rs.get_current_rankings(2026, limit=15)
for r in top:
    print(f"  #{r['rank']:2} {r['team_name']:25} {r['elo_rating']:7.1f}")
db.close()
EOF

echo ""
echo "============================================================"
echo "EPIC-029 Complete! 2026 preseason ratings are initialized."
echo "Restart the API to serve new ratings:"
echo "  sudo systemctl restart cfb-rankings"
echo "============================================================"

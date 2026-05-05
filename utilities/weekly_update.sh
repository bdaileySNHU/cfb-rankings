#!/bin/bash
# EPIC-033 Story 33.3: Automated Weekly Update
#
# Runs every Monday morning via cron to:
#   1. Pull the latest game schedule from CFBD (picks up newly announced games)
#   2. Import any completed game results from the previous weekend
#   3. Process results through the ELO algorithm
#   4. Save a ranking_history snapshot for the week
#   5. Restart the API service so fresh rankings are served immediately
#
# Cron entry (run as bdailey, 9am every Monday):
#   0 9 * * 1 /var/www/cfb-rankings/utilities/weekly_update.sh >> /var/log/cfb-rankings/weekly.log 2>&1
#
# Logs: /var/log/cfb-rankings/weekly.log
# Env:  CFBD_API_KEY must be set (loaded from systemd env or .env)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_DIR="/var/log/cfb-rankings"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ── Ensure log directory exists ───────────────────────────────────────────────
mkdir -p "$LOG_DIR"

echo ""
echo "========================================================================"
echo "  Stat-urday Weekly Update — $TIMESTAMP"
echo "========================================================================"

cd "$PROJECT_DIR"

# ── Load CFBD_API_KEY from .env if not already set ────────────────────────────
if [ -z "${CFBD_API_KEY:-}" ]; then
    if [ -f "$PROJECT_DIR/.env" ]; then
        export $(grep -v '^#' "$PROJECT_DIR/.env" | grep CFBD_API_KEY | xargs)
    fi
fi

if [ -z "${CFBD_API_KEY:-}" ]; then
    echo "✗ ERROR: CFBD_API_KEY not set. Aborting."
    exit 1
fi
echo "✓ CFBD_API_KEY loaded"

# ── Detect active season ──────────────────────────────────────────────────────
SEASON=$("$PYTHON" - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Season
db = SessionLocal()
s = db.query(Season).filter(Season.is_active == True).first()
print(s.year if s else "0")
db.close()
EOF
)

if [ "$SEASON" = "0" ]; then
    echo "✗ ERROR: No active season found. Aborting."
    exit 1
fi
echo "✓ Active season: $SEASON"

# ── Step 1: Import latest schedule + results from CFBD ───────────────────────
echo ""
echo "[1/3] Importing schedule and results for season $SEASON..."
"$PYTHON" import_real_data.py --season "$SEASON" 2>&1
echo "✓ Schedule/results import complete"

# ── Step 2: Process any unprocessed games through ELO ────────────────────────
echo ""
echo "[2/3] Processing unprocessed games through ELO algorithm..."
"$PYTHON" - <<EOF
import sys
from src.models.database import SessionLocal
from src.models.models import Game, Season as SeasonModel
from src.core.ranking_service import RankingService

db = SessionLocal()
season = $SEASON

# Find unprocessed games that have scores
unprocessed = db.query(Game).filter(
    Game.season == season,
    Game.is_processed == False,
    Game.home_score != None,
    Game.away_score != None,
).order_by(Game.week.asc(), Game.game_date.asc()).all()

if not unprocessed:
    print(f"  No unprocessed games with scores found for season {season}")
    db.close()
    sys.exit(0)

print(f"  Found {len(unprocessed)} games to process...")
rs = RankingService(db)
processed_count = 0

for game in unprocessed:
    try:
        rs.process_game(game)
        db.commit()
        processed_count += 1
    except Exception as e:
        print(f"  ✗ Error processing game {game.id}: {e}")
        db.rollback()

print(f"  ✓ Processed {processed_count} games")

# Save weekly snapshot for each newly completed week
from sqlalchemy import text
weeks = db.execute(text(
    f"SELECT DISTINCT week FROM games WHERE season={season} AND is_processed=1 ORDER BY week"
)).fetchall()

for (week,) in weeks:
    try:
        rs.save_weekly_rankings(season=season, week=week)
        db.commit()
        print(f"  ✓ Saved ranking snapshot for Week {week}")
    except Exception as e:
        print(f"  ✗ Error saving snapshot for Week {week}: {e}")

db.close()
EOF
echo "✓ ELO processing complete"

# ── Step 3: Restart the API service ──────────────────────────────────────────
echo ""
echo "[3/3] Restarting cfb-rankings service..."
if sudo systemctl restart cfb-rankings 2>/dev/null; then
    echo "✓ Service restarted"
else
    echo "⚠ Could not restart service (may need sudo permissions — restart manually)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================================================"
echo "  Weekly update complete — $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================================================"
echo ""

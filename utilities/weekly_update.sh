#!/bin/bash
# EPIC-033 Story 33.3 / EPIC-035: Automated Weekly Update with Monitoring
#
# Runs every Monday morning via cron to:
#   1. Pull the latest game schedule from CFBD (with retry logic)
#   2. Import completed game results (3 attempts, exponential backoff)
#   3. Process results through the ELO algorithm
#   4. Save ranking_history snapshots for completed weeks
#   5. Compute rank diff report (teams that moved ≥5 spots)
#   6. Restart the API service
#   7. Send Slack / email notification with result summary
#
# Cron entry (run as bdailey, 9am every Monday):
#   0 9 * * 1 /var/www/cfb-rankings/utilities/weekly_update.sh >> /var/log/cfb-rankings/weekly.log 2>&1
#
# Logs:    /var/log/cfb-rankings/weekly.log
# Env vars required:
#   CFBD_API_KEY     — CollegeFootballData.com API key
# Env vars optional:
#   SLACK_WEBHOOK_URL — Slack incoming webhook for notifications
#   NOTIFY_EMAIL      — Email address to send result summary to

set -euo pipefail

# Ensure standard PATH — required when invoked via Gunicorn/systemd subprocess
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_DIR="/var/log/cfb-rankings"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
IMPORT_EXIT_CODE=0

# ── Ensure log directory exists ───────────────────────────────────────────────
mkdir -p "$LOG_DIR"

echo ""
echo "========================================================================"
echo "  Stat-urday Weekly Update — $TIMESTAMP"
echo "========================================================================"

cd "$PROJECT_DIR"

# ── Load env vars from .env if not already set ────────────────────────────────
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$PROJECT_DIR/.env" | grep -E '^[A-Z_]+=')
    set +a
fi

if [ -z "${CFBD_API_KEY:-}" ]; then
    echo "✗ ERROR: CFBD_API_KEY not set. Aborting."
    _send_notification "❌ Weekly update FAILED" "CFBD_API_KEY is not set on the server."
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
    _send_notification "❌ Weekly update FAILED" "No active season found in the database."
    exit 1
fi
echo "✓ Active season: $SEASON"

# ── Notification helper ───────────────────────────────────────────────────────
_send_notification() {
    local title="$1"
    local body="$2"

    # Slack webhook
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local payload
        payload=$(printf '{"text":"%s\\n%s"}' "$title" "$body" | sed 's/"/\\"/g')
        # Build clean JSON directly
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            --data "{\"text\":\"$title\n$body\"}" \
            --max-time 10 \
            && echo "✓ Slack notification sent" \
            || echo "⚠ Slack notification failed (continuing)"
    fi

    # Email fallback
    if [ -n "${NOTIFY_EMAIL:-}" ]; then
        if command -v mail &>/dev/null; then
            echo "$body" | mail -s "$title" "$NOTIFY_EMAIL" \
                && echo "✓ Email notification sent to $NOTIFY_EMAIL" \
                || echo "⚠ Email notification failed (continuing)"
        fi
    fi
}

# ── Step 1: Import latest schedule + results (with retry) ────────────────────
echo ""
echo "[1/4] Importing schedule and results for season $SEASON..."

MAX_ATTEMPTS=3
ATTEMPT=0
IMPORT_SUCCESS=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT / $MAX_ATTEMPTS..."

    if "$PYTHON" import_real_data.py --season "$SEASON" 2>&1; then
        IMPORT_SUCCESS=true
        echo "✓ Schedule/results import complete (attempt $ATTEMPT)"
        break
    else
        IMPORT_EXIT_CODE=$?
        if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
            BACKOFF=$((ATTEMPT * 30))
            echo "  ⚠ Import attempt $ATTEMPT failed (exit $IMPORT_EXIT_CODE). Retrying in ${BACKOFF}s..."
            sleep "$BACKOFF"
        else
            echo "  ✗ All $MAX_ATTEMPTS import attempts failed."
        fi
    fi
done

if [ "$IMPORT_SUCCESS" = "false" ]; then
    echo "✗ ERROR: Import failed after $MAX_ATTEMPTS attempts. Aborting."
    _send_notification "❌ Weekly update FAILED ($SEASON)" \
        "import_real_data.py failed after $MAX_ATTEMPTS attempts. Check /var/log/cfb-rankings/weekly.log for details."
    exit 1
fi

# ── Step 2: Process unprocessed games through ELO ────────────────────────────
echo ""
echo "[2/4] Processing unprocessed games through ELO algorithm..."
ELO_RESULT=$("$PYTHON" - <<EOF
import sys
from src.models.database import SessionLocal
from src.models.models import Game, Season as SeasonModel
from src.core.ranking_service import RankingService

db = SessionLocal()
season = $SEASON

unprocessed = db.query(Game).filter(
    Game.season == season,
    Game.is_processed == False,
    Game.home_score != None,
    Game.away_score != None,
).order_by(Game.week.asc(), Game.game_date.asc()).all()

if not unprocessed:
    print(f"NO_NEW_GAMES")
    db.close()
    sys.exit(0)

print(f"PROCESSING:{len(unprocessed)}")
rs = RankingService(db)
processed_count = 0

for game in unprocessed:
    try:
        rs.process_game(game)
        db.commit()
        processed_count += 1
    except Exception as e:
        print(f"ERROR_GAME:{game.id}:{e}")
        db.rollback()

print(f"DONE:{processed_count}")

from sqlalchemy import text
weeks = db.execute(text(
    f"SELECT DISTINCT week FROM games WHERE season={season} AND is_processed=1 ORDER BY week"
)).fetchall()

for (week,) in weeks:
    try:
        rs.save_weekly_rankings(season=season, week=week)
        db.commit()
        print(f"SNAPSHOT:{week}")
    except Exception as e:
        print(f"ERROR_SNAPSHOT:{week}:{e}")

db.close()
EOF
)

GAMES_PROCESSED=0
SNAPSHOTS_SAVED=0
while IFS= read -r line; do
    case "$line" in
        NO_NEW_GAMES)       echo "  No new games to process" ;;
        PROCESSING:*)       echo "  Found ${line#PROCESSING:} games to process..." ;;
        DONE:*)
            GAMES_PROCESSED="${line#DONE:}"
            echo "  ✓ Processed $GAMES_PROCESSED games" ;;
        SNAPSHOT:*)
            SNAPSHOTS_SAVED=$((SNAPSHOTS_SAVED + 1))
            echo "  ✓ Saved ranking snapshot for Week ${line#SNAPSHOT:}" ;;
        ERROR_GAME:*)       echo "  ✗ ${line}" ;;
        ERROR_SNAPSHOT:*)   echo "  ✗ ${line}" ;;
        *)                  echo "  $line" ;;
    esac
done <<< "$ELO_RESULT"

echo "✓ ELO processing complete ($GAMES_PROCESSED games, $SNAPSHOTS_SAVED snapshots)"

# ── Step 3: Rank diff report (teams that moved ≥5 spots) ─────────────────────
echo ""
echo "[3/4] Computing rank movement report..."
DIFF_REPORT=$("$PYTHON" - <<EOF
import sys, json
from src.models.database import SessionLocal
from src.models.models import Team
from src.models.schemas import RankingHistory as RHSchema
from src.core.ranking_service import RankingService
from sqlalchemy import text

db = SessionLocal()
season = $SEASON

# Get current rankings
rs = RankingService(db)
current = rs.get_current_rankings(season, limit=200)

# Get the most recent completed week number
row = db.execute(text(
    f"SELECT MAX(week) FROM ranking_history WHERE season={season} AND week != 999"
)).fetchone()
current_week = row[0] if row and row[0] else 0

if current_week < 1:
    print("NO_PRIOR_WEEK")
    db.close()
    sys.exit(0)

prior_week = current_week - 1

# Fetch prior-week rankings
from src.models.models import RankingHistory
prior_rows = db.query(RankingHistory).filter(
    RankingHistory.season == season,
    RankingHistory.week == prior_week,
).all()

if not prior_rows:
    print("NO_PRIOR_WEEK")
    db.close()
    sys.exit(0)

# Build prior rank from elo order
sorted_prior = sorted(prior_rows, key=lambda r: r.elo_rating, reverse=True)
prior_rank = {r.team_id: i+1 for i, r in enumerate(sorted_prior)}

movers = []
for entry in current:
    tid = entry["team_id"]
    cur_rank = entry["rank"]
    prev = prior_rank.get(tid)
    if prev is None:
        continue
    delta = prev - cur_rank  # positive = moved up
    if abs(delta) >= 5:
        direction = "▲" if delta > 0 else "▼"
        movers.append({
            "team": entry["team_name"],
            "prev": prev,
            "cur": cur_rank,
            "delta": delta,
            "direction": direction,
        })

movers.sort(key=lambda m: abs(m["delta"]), reverse=True)

# Write to import log as diff_report field
import json
from pathlib import Path

log_path = Path("data/import_log.json")
if log_path.exists():
    with open(log_path) as f:
        log_data = json.load(f)
else:
    log_data = {}

log_data["diff_report"] = movers
log_data["diff_week"] = current_week
log_path.parent.mkdir(parents=True, exist_ok=True)
with open(log_path, "w") as f:
    json.dump(log_data, f, indent=2)

if movers:
    print(f"MOVERS:{len(movers)}")
    for m in movers[:10]:
        print(f"MOVER:{m['direction']}{abs(m['delta'])} {m['team']} ({m['prev']}→{m['cur']})")
else:
    print("NO_MOVERS")

db.close()
EOF
)

DIFF_TEXT=""
MOVER_COUNT=0
while IFS= read -r line; do
    case "$line" in
        NO_PRIOR_WEEK)  echo "  No prior week data — skipping diff" ;;
        NO_MOVERS)      echo "  No teams moved 5+ spots this week" ;;
        MOVERS:*)
            MOVER_COUNT="${line#MOVERS:}"
            echo "  $MOVER_COUNT team(s) moved 5+ spots" ;;
        MOVER:*)
            entry="${line#MOVER:}"
            DIFF_TEXT="$DIFF_TEXT\n• $entry"
            echo "  $entry" ;;
        *)              echo "  $line" ;;
    esac
done <<< "$DIFF_REPORT"

echo "✓ Rank diff report complete"

# ── Step 4: Restart the API service ──────────────────────────────────────────
echo ""
echo "[4/4] Restarting cfb-rankings service..."
if sudo systemctl restart cfb-rankings 2>/dev/null; then
    echo "✓ Service restarted"
else
    echo "⚠ Could not restart service (may need sudo permissions — restart manually)"
fi

# ── Send success notification ─────────────────────────────────────────────────
NOTIFY_BODY="Season $SEASON | Processed: $GAMES_PROCESSED games | Snapshots: $SNAPSHOTS_SAVED"
if [ -n "$DIFF_TEXT" ]; then
    NOTIFY_BODY="$NOTIFY_BODY\n\nBig movers (5+ spots):\n$DIFF_TEXT"
fi
_send_notification "✅ Weekly update complete ($SEASON)" "$NOTIFY_BODY"

# ── Write final import log ─────────────────────────────────────────────────────
"$PYTHON" - <<EOF
import json, datetime
from pathlib import Path

log_path = Path("data/import_log.json")
if log_path.exists():
    with open(log_path) as f:
        log_data = json.load(f)
else:
    log_data = {}

log_data.update({
    "last_run": datetime.datetime.utcnow().isoformat() + "Z",
    "season": $SEASON,
    "games_processed": $GAMES_PROCESSED,
    "status": "success",
    "error": None,
})
log_path.parent.mkdir(parents=True, exist_ok=True)
with open(log_path, "w") as f:
    json.dump(log_data, f, indent=2)
print("✓ Import log updated")
EOF

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================================================"
echo "  Weekly update complete — $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================================================"
echo ""

#!/bin/bash
# Import Playoff Games and Generate Predictions
# Execute this script as www-data user: sudo -u www-data bash import_playoff_games.sh

set -e  # Exit on error

echo "=== Importing Playoff Games ==="
echo "CFBD API verification: 2 upcoming CFP semifinal games available"
echo "  - Miami at Ole Miss (Fiesta Bowl) - Jan 9, 2026"
echo "  - Oregon at Indiana (Peach Bowl) - Jan 10, 2026"
echo

# Load environment variables
cd /var/www/cfb-rankings
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Environment variables loaded from .env"
else
    echo "⚠ Warning: .env file not found"
fi
echo

echo "Step 1: Importing games from CFBD API..."
source venv/bin/activate && python3 scripts/weekly_update.py

echo
echo "Step 2: Generating predictions for all unprocessed games..."
echo "Note: Using generate_all_predictions.py to include playoff games"
source venv/bin/activate && python3 scripts/generate_all_predictions.py

echo
echo "=== Verification ==="
echo "Checking imported playoff games..."
sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM games WHERE season = 2025 AND is_processed = 0 AND postseason_name IS NOT NULL;'

echo
echo "Checking generated predictions..."
sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM predictions p JOIN games g ON p.game_id = g.id WHERE g.season = 2025 AND g.postseason_name IS NOT NULL AND g.is_processed = 0;'

echo
echo "=== Showing Playoff Games Details ==="
sqlite3 -header -column cfb_rankings.db "
SELECT
    g.id,
    ht.name as home_team,
    at.name as away_team,
    g.game_date,
    g.postseason_name
FROM games g
JOIN teams ht ON g.home_team_id = ht.id
JOIN teams at ON g.away_team_id = at.id
WHERE g.season = 2025
  AND g.is_processed = 0
  AND g.postseason_name IS NOT NULL
ORDER BY g.game_date;
"

echo
echo "=== Done ==="
echo "Visit https://cfb.bdailey.com to verify predictions are displayed"

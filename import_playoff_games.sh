#!/bin/bash
# Import Playoff Games and Generate Predictions
# Execute this script as www-data user: sudo -u www-data bash import_playoff_games.sh

set -e  # Exit on error

echo "=== Importing Playoff Games ==="
echo "CFBD API verification: 2 upcoming CFP semifinal games available"
echo "  - Miami at Ole Miss (Fiesta Bowl) - Jan 9, 2026"
echo "  - Oregon at Indiana (Peach Bowl) - Jan 10, 2026"
echo

echo "Step 1: Importing games from CFBD API..."
cd /var/www/cfb-rankings
source venv/bin/activate && python3 scripts/weekly_update.py

echo
echo "Step 2: Generating predictions..."
source venv/bin/activate && python3 scripts/generate_predictions.py

echo
echo "=== Verification ==="
echo "Checking imported playoff games..."
cd /var/www/cfb-rankings && sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM games WHERE season = 2025 AND is_processed = FALSE AND postseason_name IS NOT NULL;'

echo
echo "Checking generated predictions..."
cd /var/www/cfb-rankings && sqlite3 cfb_rankings.db 'SELECT COUNT(*) FROM predictions p JOIN games g ON p.game_id = g.id WHERE g.season = 2025 AND g.postseason_name IS NOT NULL AND g.is_processed = FALSE;'

echo
echo "=== Showing Playoff Games Details ==="
cd /var/www/cfb-rankings && sqlite3 -header -column cfb_rankings.db 'SELECT id, home_team, away_team, game_date, postseason_name FROM games WHERE season = 2025 AND is_processed = FALSE AND postseason_name IS NOT NULL ORDER BY game_date;'

echo
echo "=== Done ==="
echo "Visit https://cfb.bdailey.com to verify predictions are displayed"

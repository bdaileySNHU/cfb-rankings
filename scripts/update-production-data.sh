#!/bin/bash
# Production Game Data Update Script
# Handles permissions and runs update_games.py safely

set -e

APP_DIR="/var/www/cfb-rankings"
LOG_FILE="/var/log/cfb-rankings/update-games.log"

echo "========================================="
echo "College Football Rankings - Data Update"
echo "========================================="
echo ""

# Create log directory if needed
sudo mkdir -p /var/log/cfb-rankings
sudo chown www-data:www-data /var/log/cfb-rankings

# Navigate to app directory
cd "$APP_DIR"

echo "Step 1: Checking permissions..."

# Fix database permissions
sudo chmod 664 cfb_rankings.db 2>/dev/null || true
sudo chmod 775 . 2>/dev/null || true
sudo chown www-data:www-data cfb_rankings.db
sudo chown www-data:www-data .

echo "✓ Permissions fixed"
echo ""

echo "Step 2: Running update script..."
echo "This will fetch new games from CollegeFootballData.com API"
echo ""

# Run as www-data user
sudo -u www-data bash -c "source venv/bin/activate && python3 update_games.py"

echo ""
echo "Step 3: Restarting backend service..."

# Restart backend to load fresh data
sudo systemctl restart cfb-rankings

# Wait for service to start
sleep 3

# Check if service started successfully
if sudo systemctl is-active --quiet cfb-rankings; then
    echo "✓ Backend service restarted successfully"
else
    echo "⚠ Warning: Backend service may not have started correctly"
    echo "Check status with: sudo systemctl status cfb-rankings"
fi

echo ""
echo "Step 4: Verifying update..."

# Check current week in database
CURRENT_WEEK=$(sqlite3 cfb_rankings.db "SELECT MAX(week) FROM games WHERE season = 2025;")
echo "✓ Database now contains games through Week $CURRENT_WEEK"

echo ""
echo "========================================="
echo "Update Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Visit: https://cfb.bdailey.com"
echo "  2. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)"
echo "  3. Verify rankings show Week $CURRENT_WEEK data"
echo ""

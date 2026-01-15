#!/bin/bash
# Clear Python cache and restart service
# Run this on the VPS when code changes aren't being picked up

set -e

APP_DIR="/var/www/cfb-rankings"
SERVICE_NAME="cfb-rankings"

echo "==========================================="
echo "Clearing Python Cache & Restarting Service"
echo "==========================================="
echo ""

# Stop the service first
echo "🛑 Stopping service..."
systemctl stop $SERVICE_NAME

# Clear Python cache
echo "🧹 Clearing Python cache..."
cd $APP_DIR
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Start the service
echo "🚀 Starting service..."
systemctl start $SERVICE_NAME
sleep 2
systemctl status $SERVICE_NAME --no-pager

echo ""
echo "✅ Cache cleared and service restarted!"
echo ""
echo "Test the API:"
echo "  curl https://cfb.bdailey.com/api/predictions/comparison?season=2025 | python3 -m json.tool | tail -30"
echo ""

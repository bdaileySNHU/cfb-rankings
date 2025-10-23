#!/bin/bash
# EPIC-009 Deployment Script
# Prediction Accuracy Tracking & Display
# Version: 3.0.0
# Risk: LOW (no database migration required)

set -e  # Exit on error

echo "=========================================="
echo "EPIC-009 Deployment"
echo "Prediction Accuracy Tracking & Display"
echo "Version 3.0.0 | Risk: LOW"
echo "=========================================="
echo ""

# Configuration
APP_DIR="/var/www/cfb-rankings"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="cfb-rankings"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "📦 Step 1: Pulling latest code from GitHub..."
cd $APP_DIR
git pull origin main

echo ""
echo "🔍 Step 2: Verifying EPIC-009 commits..."
git log --oneline -5 | head -5

echo ""
echo "🔄 Step 3: Restarting application service..."
systemctl restart $SERVICE_NAME

echo ""
echo "✅ Step 4: Checking service status..."
systemctl status $SERVICE_NAME --no-pager -l | head -20

echo ""
echo "🧪 Step 5: Testing EPIC-009 API endpoints..."

# Test prediction accuracy endpoint
echo "  Testing /api/predictions/accuracy..."
curl -s http://localhost:8000/api/predictions/accuracy?season=2024 > /dev/null && echo "  ✅ Overall accuracy endpoint OK" || echo "  ❌ Overall accuracy endpoint FAILED"

# Test team prediction accuracy endpoint
echo "  Testing /api/predictions/accuracy/team/82..."
curl -s http://localhost:8000/api/predictions/accuracy/team/82?season=2024 > /dev/null && echo "  ✅ Team accuracy endpoint OK" || echo "  ❌ Team accuracy endpoint FAILED"

# Test stored predictions endpoint
echo "  Testing /api/predictions/stored..."
curl -s "http://localhost:8000/api/predictions/stored?season=2024&evaluated_only=true" > /dev/null && echo "  ✅ Stored predictions endpoint OK" || echo "  ❌ Stored predictions endpoint FAILED"

echo ""
echo "=========================================="
echo "✅ EPIC-009 Deployment Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "  1. Visit https://cfb.bdailey.com in your browser"
echo "  2. Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)"
echo "  3. Verify prediction accuracy banner on rankings page"
echo "  4. Check team pages for prediction accuracy stats"
echo ""
echo "Monitor logs with:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""

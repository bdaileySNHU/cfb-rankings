#!/bin/bash
# Hotfix: Update api.js to use production API URL
# Issue: CORS errors due to localhost hardcoded in production
# Date: 2025-10-17

set -e

echo "========================================="
echo "Hotfix: API URL Configuration"
echo "========================================="
echo ""

# Configuration
LOCAL_FILE="frontend/js/api.js"
SERVER_USER="your-username"  # CHANGE THIS
SERVER_HOST="cfb.bdailey.com"  # Your server
SERVER_PATH="/var/www/cfb-rankings/frontend/js"

echo "Step 1: Verify local file exists"
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Error: $LOCAL_FILE not found"
    exit 1
fi
echo "✓ File found: $LOCAL_FILE"
echo ""

echo "Step 2: Show the change being deployed"
echo "----------------------------------------"
grep -A 2 "const API_BASE_URL" "$LOCAL_FILE"
echo "----------------------------------------"
echo ""

echo "Step 3: Deploy to production server"
read -p "Continue with deployment to $SERVER_HOST? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

echo ""
echo "Uploading file to server..."

# Upload to temp location first
scp "$LOCAL_FILE" "$SERVER_USER@$SERVER_HOST:/tmp/api.js"

echo "✓ File uploaded to /tmp/"
echo ""

echo "Step 4: Install on server (requires sudo)"
echo "Run these commands on your server:"
echo ""
echo "  ssh $SERVER_USER@$SERVER_HOST"
echo "  sudo cp /tmp/api.js $SERVER_PATH/api.js"
echo "  sudo chown www-data:www-data $SERVER_PATH/api.js"
echo "  sudo chmod 644 $SERVER_PATH/api.js"
echo "  rm /tmp/api.js"
echo ""

echo "Step 5: Verify in browser"
echo "  1. Visit: https://cfb.bdailey.com"
echo "  2. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)"
echo "  3. Check browser console (F12) - should see no CORS errors"
echo "  4. Rankings should load successfully"
echo ""

echo "========================================="
echo "Manual deployment instructions provided"
echo "========================================="

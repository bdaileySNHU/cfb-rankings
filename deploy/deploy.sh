#!/bin/bash
# Deployment script for College Football Rankings
# Run this on your VPS after initial setup

set -e  # Exit on error

echo "=========================================="
echo "College Football Rankings - Deployment"
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

# Pull latest code
echo "📦 Pulling latest code..."
cd $APP_DIR
git pull origin main

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements-prod.txt

# Run database migrations (if any)
# Note: Only needed for initial setup or schema changes
# Commenting out for regular deployments
# echo "🗄️  Setting up database..."
# python3 -c "from src.models.database import init_db; init_db()"

# Restart the service
echo "🔄 Restarting service..."
systemctl restart $SERVICE_NAME
systemctl status $SERVICE_NAME --no-pager

# Reload Nginx
echo "🔄 Reloading Nginx..."
nginx -t && systemctl reload nginx

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Check logs with:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""

#!/bin/bash
# EPIC-004 Deployment Script for VPS
# This script deploys all EPIC-004 changes to production

set -e  # Exit on any error

echo "========================================"
echo "EPIC-004 Deployment Script"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="/var/www/cfb-rankings"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/log/cfb-rankings"

echo -e "${BLUE}Step 1: Pulling latest code from Git...${NC}"
cd $PROJECT_DIR
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

echo -e "${BLUE}Step 2: Checking .env configuration...${NC}"
if ! grep -q "CFBD_MONTHLY_LIMIT" "$PROJECT_DIR/.env"; then
    echo -e "${YELLOW}⚠ CFBD_MONTHLY_LIMIT not found in .env${NC}"
    echo "Please add this line to your .env file:"
    echo "  CFBD_MONTHLY_LIMIT=1000"
    echo ""
    read -p "Press Enter after you've added it (or Ctrl+C to exit)..."
else
    echo -e "${GREEN}✓ CFBD_MONTHLY_LIMIT configured${NC}"
fi
echo ""

echo -e "${BLUE}Step 3: Installing Python dependencies...${NC}"
source $VENV_DIR/bin/activate
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo -e "${BLUE}Step 4: Updating database schema...${NC}"
python3 << 'PYEOF'
from database import engine, Base
from models import APIUsage, UpdateTask
try:
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created/updated")
    print("  - api_usage table")
    print("  - update_tasks table")
except Exception as e:
    print(f"Error updating database: {e}")
    exit(1)
PYEOF
echo -e "${GREEN}✓ Database schema updated${NC}"
echo ""

echo -e "${BLUE}Step 5: Setting permissions...${NC}"
chown -R www-data:www-data $PROJECT_DIR
chmod 664 $PROJECT_DIR/cfb_rankings.db
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

echo -e "${BLUE}Step 6: Creating log directory...${NC}"
mkdir -p $LOG_DIR
chown www-data:www-data $LOG_DIR
echo -e "${GREEN}✓ Log directory created${NC}"
echo ""

echo -e "${BLUE}Step 7: Installing systemd timer and service...${NC}"
cp $PROJECT_DIR/deploy/cfb-weekly-update.timer /etc/systemd/system/
cp $PROJECT_DIR/deploy/cfb-weekly-update.service /etc/systemd/system/
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd units installed${NC}"
echo ""

echo -e "${BLUE}Step 8: Enabling and starting weekly update timer...${NC}"
systemctl enable cfb-weekly-update.timer
systemctl start cfb-weekly-update.timer
echo -e "${GREEN}✓ Timer enabled and started${NC}"
echo ""

echo -e "${BLUE}Step 9: Restarting application service...${NC}"
systemctl restart cfb-rankings
sleep 2
echo -e "${GREEN}✓ Application restarted${NC}"
echo ""

echo "========================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo ""

echo "Verifying deployment..."
echo ""

# Check application service
echo -n "Application service: "
if systemctl is-active --quiet cfb-rankings; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${RED}STOPPED${NC}"
    echo "Check logs: sudo journalctl -u cfb-rankings -n 50"
fi

# Check timer
echo -n "Weekly update timer: "
if systemctl is-active --quiet cfb-weekly-update.timer; then
    echo -e "${GREEN}ACTIVE${NC}"
else
    echo -e "${RED}INACTIVE${NC}"
fi

# Show next timer run
echo ""
echo "Next scheduled update:"
systemctl list-timers cfb-weekly-update.timer --no-pager | tail -n +2

echo ""
echo "Testing endpoints..."
echo ""

# Test endpoints
echo -n "Health check: "
if curl -s http://localhost:8000/ | grep -q "ok"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

echo -n "API usage endpoint: "
if curl -s http://localhost:8000/api/admin/api-usage | grep -q "total_calls"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

echo -n "Config endpoint: "
if curl -s http://localhost:8000/api/admin/config | grep -q "cfbd_monthly_limit"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}EPIC-004 Successfully Deployed!${NC}"
echo "========================================"
echo ""
echo "New features available:"
echo "  • API usage tracking and monitoring"
echo "  • Automated weekly updates (Sundays 8 PM ET)"
echo "  • Manual update trigger endpoint"
echo "  • Usage dashboard with projections"
echo ""
echo "Useful commands:"
echo "  • View logs: sudo journalctl -u cfb-rankings -f"
echo "  • Check usage: curl http://localhost:8000/api/admin/api-usage | jq"
echo "  • View API docs: http://your-domain.com/docs"
echo ""
echo "See EPIC-004-DEPLOYMENT-GUIDE.md for complete documentation."
echo ""

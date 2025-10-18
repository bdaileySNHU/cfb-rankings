#!/bin/bash
# Deployment Script for EPIC-001: Game Schedule Display
# Created: 2025-10-17
# Developer: James (Dev Agent)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Users/bryandailey/Stat-urday Synthesis"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EPIC-001 Deployment Script${NC}"
echo -e "${BLUE}Game Schedule Display Feature${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print success message
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error message
error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print warning message
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print info message
info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Step 1: Pre-deployment checks
echo -e "${BLUE}[Step 1/6] Pre-deployment Checks${NC}"
echo "----------------------------------------"

# Check if we're in the right directory
if [ ! -d "$FRONTEND_DIR" ]; then
    error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi
success "Frontend directory found"

# Check if files exist
FILES_TO_DEPLOY=(
    "$FRONTEND_DIR/games.html"
    "$FRONTEND_DIR/js/team.js"
    "$FRONTEND_DIR/css/style.css"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ ! -f "$file" ]; then
        error "Required file not found: $file"
        exit 1
    fi
done
success "All required files present"

# Run tests
info "Running test suite..."
cd "$PROJECT_ROOT"
if make test > /tmp/epic001-test-results.txt 2>&1; then
    TEST_PASSED=$(grep "passed" /tmp/epic001-test-results.txt | tail -1)
    success "Test suite passed: $TEST_PASSED"
else
    error "Test suite failed! Check /tmp/epic001-test-results.txt"
    exit 1
fi

echo ""

# Step 2: Create backup
echo -e "${BLUE}[Step 2/6] Creating Backup${NC}"
echo "----------------------------------------"

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/epic001_pre_deployment_$TIMESTAMP"

info "Creating backup at: $BACKUP_PATH"
mkdir -p "$BACKUP_PATH"

cp "$FRONTEND_DIR/games.html" "$BACKUP_PATH/"
cp "$FRONTEND_DIR/js/team.js" "$BACKUP_PATH/"
cp "$FRONTEND_DIR/css/style.css" "$BACKUP_PATH/"

success "Backup created successfully"
info "Backup location: $BACKUP_PATH"

echo ""

# Step 3: Display changes summary
echo -e "${BLUE}[Step 3/6] Changes Summary${NC}"
echo "----------------------------------------"

info "Files to be deployed:"
echo "  1. frontend/games.html - Enhanced displayGames() with null-safe game handling"
echo "  2. frontend/js/team.js - Enhanced createScheduleRow() for future games"
echo "  3. frontend/css/style.css - Added .game-scheduled styling + mobile responsive"

echo ""
info "Changes:"
echo "  • Games page now displays completed and scheduled games"
echo "  • Team detail page shows complete season schedules"
echo "  • Visual distinction between played and future games"
echo "  • Smooth transitions and hover effects"
echo "  • Mobile-responsive design"

echo ""

# Step 4: Confirm deployment
echo -e "${BLUE}[Step 4/6] Deployment Confirmation${NC}"
echo "----------------------------------------"

warning "This will update the frontend files in production."
info "Backup created at: $BACKUP_PATH"
echo ""
read -p "Do you want to proceed with deployment? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    warning "Deployment cancelled by user"
    exit 0
fi

echo ""

# Step 5: Deploy files
echo -e "${BLUE}[Step 5/6] Deploying Files${NC}"
echo "----------------------------------------"

# Note: In this case, files are already in place since we're developing locally
# In a real deployment, you would copy files to production server here

info "Files are already in correct location (local development)"
success "Deployment complete"

# Check if there's a web server process to restart
if lsof -ti:8080 > /dev/null 2>&1; then
    warning "HTTP server detected on port 8080"
    read -p "Restart web server? (yes/no): " RESTART
    if [ "$RESTART" = "yes" ]; then
        info "Restarting web server..."
        kill $(lsof -ti:8080) 2>/dev/null || true
        sleep 1
        cd "$FRONTEND_DIR" && python3 -m http.server 8080 > /dev/null 2>&1 &
        success "Web server restarted"
    fi
fi

echo ""

# Step 6: Post-deployment verification
echo -e "${BLUE}[Step 6/6] Post-Deployment Verification${NC}"
echo "----------------------------------------"

info "Running verification checks..."

# Check if backend API is running
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    success "Backend API is running (port 8000)"
else
    warning "Backend API is not responding (port 8000)"
fi

# Check if frontend is accessible
if curl -s http://localhost:8080/games.html > /dev/null 2>&1; then
    success "Frontend is accessible (port 8080)"
else
    warning "Frontend is not accessible (port 8080)"
fi

# Verify games page loads
if curl -s http://localhost:8080/games.html | grep -q "game-scheduled" 2>/dev/null; then
    success "Games page contains new code"
else
    warning "Games page may not have new code (check browser cache)"
fi

echo ""

# Step 7: Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

info "Deployed Features:"
echo "  ✓ Game schedule display (completed + scheduled games)"
echo "  ✓ Enhanced team detail schedules"
echo "  ✓ Visual styling with smooth transitions"
echo "  ✓ Mobile-responsive design"
echo ""

info "Testing:"
echo "  • Visit: http://localhost:8080/games.html"
echo "  • Visit: http://localhost:8080/team.html?id=3"
echo "  • Check browser console for errors (F12)"
echo "  • Test on mobile viewport (resize browser)"
echo ""

info "Backup Location:"
echo "  $BACKUP_PATH"
echo ""

info "Rollback Command (if needed):"
echo "  cp $BACKUP_PATH/* $FRONTEND_DIR/"
echo "  cp $BACKUP_PATH/team.js $FRONTEND_DIR/js/"
echo "  cp $BACKUP_PATH/style.css $FRONTEND_DIR/css/"
echo ""

info "Documentation:"
echo "  • Epic Summary: docs/EPIC-001-COMPLETION-SUMMARY.md"
echo "  • Story 001: docs/stories/story-001-games-page-display.md"
echo "  • Story 002: docs/stories/story-002-team-detail-schedule.md"
echo "  • Story 003: docs/stories/story-003-visual-enhancements.md"
echo ""

success "EPIC-001 deployment completed successfully!"
echo ""

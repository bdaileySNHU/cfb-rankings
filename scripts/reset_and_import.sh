#!/bin/bash
# Reset and Import Script
#
# This script performs a FULL DATABASE RESET and reimports all data from scratch.
#
# WARNING: This will DELETE ALL DATA including:
#   - All games and game results
#   - All team data and ELO ratings
#   - All predictions and accuracy data
#   - All ranking history
#   - Manual corrections (like current_week adjustments)
#
# Use this script ONLY when you need to:
#   - Start completely fresh with a clean database
#   - Fix major data corruption issues
#   - Switch to a different season
#
# For normal weekly updates, use incremental mode instead:
#   python3 import_real_data.py
#
# Usage:
#   ./scripts/reset_and_import.sh
#   ./scripts/reset_and_import.sh --season 2024 --max-week 10

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "================================================================================================"
echo -e "${RED}WARNING: FULL DATABASE RESET${NC}"
echo "================================================================================================"
echo ""
echo "This script will:"
echo "  ✗ DELETE all games and results"
echo "  ✗ DELETE all team data and ELO ratings"
echo "  ✗ DELETE all predictions and accuracy data"
echo "  ✗ DELETE all ranking history"
echo "  ✗ DELETE manual corrections (like current_week adjustments)"
echo ""
echo "Then reimport everything from scratch using the CFBD API."
echo ""
echo -e "${YELLOW}For normal weekly updates, you should use incremental mode instead:${NC}"
echo "  python3 import_real_data.py"
echo ""
echo "================================================================================================"
echo ""
read -p "Are you ABSOLUTELY SURE you want to reset the database? Type 'yes' to continue: " -r
echo ""

if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Reset cancelled."
    exit 0
fi

echo ""
echo "================================================================================================"
echo -e "${GREEN}Starting Full Database Reset...${NC}"
echo "================================================================================================"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if CFBD_API_KEY is set
if [ -z "$CFBD_API_KEY" ]; then
    echo -e "${RED}ERROR: CFBD_API_KEY environment variable is not set${NC}"
    echo ""
    echo "Please set your API key:"
    echo "  export CFBD_API_KEY='your-api-key-here'"
    echo ""
    echo "Get a free API key at: https://collegefootballdata.com/key"
    exit 1
fi

# Run import with --reset flag and forward any additional arguments
echo "Running: python3 import_real_data.py --reset $@"
echo ""
python3 import_real_data.py --reset "$@"

echo ""
echo "================================================================================================"
echo -e "${GREEN}✓ Database Reset and Import Complete!${NC}"
echo "================================================================================================"
echo ""
echo "Your database has been completely rebuilt from scratch."
echo ""
echo "For future updates, use incremental mode to preserve your data:"
echo "  python3 import_real_data.py"
echo ""

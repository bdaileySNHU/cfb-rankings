#!/bin/bash
# EPIC-029: 2026 Preseason Setup
# Run this on the VPS from /var/www/cfb-rankings
# Usage: bash utilities/setup_2026_preseason.sh

set -e
PYTHON="sudo -u www-data venv/bin/python"
cd /var/www/cfb-rankings

echo "============================================================"
echo "EPIC-029: 2026 Preseason Setup"
echo "============================================================"
echo ""

# Step 1: Backup
echo "[Step 1] Backing up database..."
cp cfb_rankings.db cfb_rankings.db.backup_pre_29.1
echo "  ✓ Backup created: cfb_rankings.db.backup_pre_29.1"
echo ""

# Step 2: Reprocess 2025 season
echo "[Step 2] Reprocessing 2025 season (fixes ELO imbalances)..."
$PYTHON utilities/reprocess_season.py --season 2025
echo ""

# Step 3: Archive 2024 season
echo "[Step 3] Archiving 2024 season..."
$PYTHON - <<'EOF'
from src.models.database import SessionLocal
from src.models.models import Season
db = SessionLocal()
s = db.query(Season).filter(Season.year == 2024).first()
if s:
    s.is_active = False
    db.commit()
    print("  ✓ 2024 archived")
else:
    print("  ⚠ 2024 season not found")
for s in db.query(Season).order_by(Season.year.desc()).all():
    status = "ACTIVE" if s.is_active else "archived"
    print(f"  {s.year}: {status}, week={s.current_week}")
db.close()
EOF
echo ""

echo "============================================================"
echo "Steps 1-3 complete."
echo ""
echo "Next: run the player data import (Story 29.3):"
echo "  sudo -E -u www-data venv/bin/python utilities/import_player_data.py --year 2025"
echo "  sudo -E -u www-data venv/bin/python utilities/import_player_data.py --year 2024"
echo "  sudo -E -u www-data venv/bin/python utilities/import_player_data.py --year 2023"
echo "  sudo -E -u www-data venv/bin/python utilities/import_player_data.py --year 2022"
echo "  sudo -E -u www-data venv/bin/python utilities/import_player_data.py --year 2026"
echo ""
echo "Then run: bash utilities/finalize_2026_preseason.sh"
echo "============================================================"

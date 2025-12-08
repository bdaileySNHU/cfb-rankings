# Diagnostic Scripts

This directory contains diagnostic and debugging scripts for troubleshooting the Stat-urday Synthesis ranking system.

## Purpose

Diagnostic scripts help investigate system behavior, verify data integrity, and debug issues. Unlike migration scripts (run once), diagnostic scripts are run as needed when troubleshooting problems.

## Script Categories

### Check Scripts (`check_*.py`)
Verify system state and data integrity.

| Script | Purpose |
|--------|---------|
| `check_conference_championships.py` | Verify conference championship games in database |
| `check_game_details.py` | Inspect specific game data and scoring |
| `check_postseason_column.py` | Verify postseason game classification |
| `check_prediction_accuracy.py` | Check prediction accuracy statistics |
| `check_ranking_history.py` | Verify ranking history data consistency |
| `check_ranking_history_data.py` | Deep check of ranking history integrity |
| `check_team_games.py` | Verify team game counts and schedules |

### Debug Scripts (`debug_*.py`)
Interactive debugging and investigation tools.

| Script | Purpose |
|--------|---------|
| `debug_championships.py` | Debug championship game processing issues |

### Diagnose Scripts (`diagnose_*.py`)
Identify root causes of problems.

| Script | Purpose |
|--------|---------|
| `diagnose_missing_games.py` | Find and report missing game data |

## Usage

### Running Diagnostic Scripts

```bash
# From project root
python diagnostics/check_ranking_history.py

# With arguments (if supported)
python diagnostics/check_team_games.py --season 2024
```

### When to Run

- **After data imports** - Verify data integrity
- **After schema changes** - Ensure migrations worked correctly
- **When bugs reported** - Investigate issues
- **Before deployments** - Validate system state
- **During development** - Verify new features

### Output

Most diagnostic scripts:
- Print results to stdout
- Return exit code 0 for success
- Return non-zero exit code for failures
- May write detailed logs to files

## Best Practices

1. **Run from project root** - Scripts expect to be run from `/Users/bryandailey/Stat-urday Synthesis`
2. **Check script help** - Many scripts support `--help` flag
3. **Backup before fixes** - If script suggests fixes, backup database first
4. **Document issues** - Save script output when reporting bugs
5. **Don't modify** - Diagnostic scripts should be read-only (no database changes)

## Adding New Diagnostics

When creating new diagnostic scripts:

1. **Naming convention:**
   - `check_*.py` - Verification scripts
   - `debug_*.py` - Interactive debugging
   - `diagnose_*.py` - Problem identification

2. **Script structure:**
```python
"""Brief description of what this script checks"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Team, Game
from database import SessionLocal

def main():
    """Main diagnostic logic"""
    # Your code here
    pass

if __name__ == "__main__":
    main()
```

3. **Update this README** - Add entry to appropriate table above

## Related Directories

- `migrations/` - Database schema migrations (run once)
- `scripts/` - Operational scripts (data imports, updates)
- `utilities/` - General utility scripts (TBD in Story 28.6)

# Archive Directory

## ⚠️ WARNING: Historical Scripts Only

**DO NOT RUN THESE SCRIPTS** unless you fully understand their purpose and the specific issue they were created to address.

## Purpose

This directory contains one-off scripts that were created to fix specific issues or perform one-time data manipulations during the organic growth of the project. They are kept for historical reference and to preserve the git history of the project.

## When Were These Created?

These scripts were created over the course of 28 epics spanning several months to address specific issues that arose during development and operation. They served their purpose and are no longer needed for regular operations.

## Script Categories

### Fix Scripts (fix_*.py)
One-time fixes for specific data issues that occurred during development:
- Data inconsistencies
- Schema migration corrections
- Playoff/championship processing issues
- Week/season data corrections

### Recalculation Scripts (recalculate_*.py)
One-time recalculations of rankings when algorithm changes required historical data updates:
- Algorithm parameter adjustments
- K-factor modifications
- ELO rating recalibrations

### Data Population Scripts (save_*.py, add_*.py)
One-time scripts for populating or correcting historical data:
- Championship week rankings
- Historical ranking snapshots
- Postseason column additions

### Analysis Scripts (count_*.py, find_*.py, verify_*.py)
One-time analysis scripts created to investigate specific issues:
- Data verification
- Championship team identification
- Game count analysis

### Comparison Scripts (compare_*.py)
One-time comparison scripts for evaluating different approaches

### Optimization Scripts (optimize_*.py)
One-time parameter optimization experiments

## If You Need to Run a Script

1. **Read the script carefully** - Understand exactly what it does
2. **Check git history** - Run `git log --follow archive/script_name.py` to see why it was created
3. **Check if still relevant** - The issue may have been resolved long ago
4. **Backup your database** - Before running any script that modifies data: `cp cfb_rankings.db cfb_rankings.db.backup`
5. **Test in development** - Never run directly in production without testing
6. **Verify imports** - Scripts may need import path updates after reorganization

## Regular Operations

For regular operations, use the appropriate directory:

- **Production operations**: `scripts/` directory
  - `weekly_update.py` - Automated weekly data import
  - `generate_predictions.py` - Generate game predictions
  - `backfill_*.py` - Historical data backfill

- **Data import**: `import_real_data.py` in root directory

- **Diagnostics**: `diagnostics/` directory
  - `check_*.py` - Data verification
  - `debug_*.py` - Debugging tools
  - `diagnose_*.py` - Problem identification

- **Utilities**: `utilities/` directory
  - `seed_data.py` - Generate sample data
  - `demo.py` - Standalone ranking demo
  - Evaluation and comparison tools

- **Database migrations**: `migrations/` directory
  - Schema changes and data migrations

## Archive History

Archived during **EPIC-028: Comprehensive Codebase Cleanup (Story 28.7)**
- Date: December 2025
- Purpose: Clean up root directory and organize codebase
- Scripts moved: 15-20 one-off and obsolete scripts

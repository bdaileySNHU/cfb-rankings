# Utilities Directory

## Purpose

This directory contains reusable helper scripts and tools for development, testing, evaluation, and analysis of the ranking system.

Unlike the scripts in `archive/` (which are one-off historical fixes), these utilities are designed to be run multiple times for various purposes during development and analysis.

## Utility Categories

### Development Tools

**seed_data.py** - Generate sample data for testing
- Creates sample teams, games, and seasons
- Useful for local development and testing
- Safe to run multiple times (use with caution - may reset data)

```bash
python utilities/seed_data.py
```

**demo.py** - Standalone ELO ranking demonstration
- Shows how the Modified ELO algorithm works
- Runs independently without database
- Educational tool for understanding the ranking system

```bash
python utilities/demo.py
```

### Analysis and Comparison Tools

**compare_rankings.py** - Compare ELO rankings with AP Poll
- Analyzes correlation between Modified ELO and AP Poll rankings
- Generates comparison metrics and visualizations
- Useful for validating ranking system performance

```bash
python utilities/compare_rankings.py
```

**compare_transfer_rankings.py** - Compare transfer portal ranking methods
- Evaluates different approaches to ranking transfer portal classes
- Star-based vs rating-based comparisons
- Used during EPIC-026 development

```bash
python utilities/compare_transfer_rankings.py
```

**evaluate_rating_systems.py** - Evaluate and compare different rating systems
- Tests different ELO parameters and approaches
- Compares prediction accuracy across configurations
- Research and development tool

```bash
python utilities/evaluate_rating_systems.py
```

## Usage Guidelines

### Safe to Run
All utilities in this directory are safe to run for their intended purposes. However:

- **seed_data.py** may modify or reset your database - use with caution
- **Analysis tools** are read-only and safe for production data

### Import Paths
After the src/ reorganization (Story 28.6), utilities may need to import from:
```python
from src.models.models import Team, Game
from src.models.database import get_db
from src.core.ranking_service import RankingService
```

### When to Use

- **Development**: Use seed_data.py to populate test data
- **Learning**: Use demo.py to understand the algorithm
- **Analysis**: Use comparison and evaluation tools to validate performance
- **Research**: Use evaluation tools when testing algorithm changes

## Related Directories

- **scripts/** - Production operational scripts (weekly updates, predictions)
- **diagnostics/** - Diagnostic and debugging tools
- **migrations/** - Database schema migrations
- **archive/** - Historical one-off scripts (do not run)

## Contributing New Utilities

When adding new utilities:
1. Make them reusable (not one-off fixes)
2. Add clear docstrings and usage examples
3. Update this README with the new utility
4. Test with both sample and production data
5. Document any database modifications clearly

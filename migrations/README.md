# Database Migrations

This directory contains database schema migration scripts for the Stat-urday Synthesis ranking system.

## Purpose

Migration scripts handle database schema changes and data transformations that occur as the system evolves. Each migration should be run once when deploying a new feature that requires database changes.

## Naming Convention

- **Python migrations:** `migrate_add_*.py` - Adds new columns/tables
- **SQL migrations:** `NNN_description.sql` - Raw SQL migrations
- **Migration runners:** `run_migration_*.py` - Orchestration scripts

## Usage

### Running a Migration

```bash
# From project root
python migrations/migrate_add_predictions.py
```

### Best Practices

1. **Run once** - Each migration should be executed only once per database
2. **Test first** - Test migrations on development database before production
3. **Backup** - Always backup the database before running migrations
4. **Document** - Add entry to migration list below after running

## Migration History

| Date | Script | Purpose | Status |
|------|--------|---------|--------|
| 2024-12-01 | `001_add_postseason_name.sql` | Add postseason_name column to games table | ✅ Complete |
| 2024-12-01 | `run_migration_001.py` | Run SQL migration 001 | ✅ Complete |
| 2024-10-18 | `migrate_add_fcs_fields.py` | Add FCS-related fields to teams/games tables | ✅ Complete |
| 2024-10-XX | `migrate_add_predictions.py` | Add predictions table for EPIC-009 | ✅ Complete |
| 2024-11-XX | `migrate_add_quarter_scores.py` | Add quarter-by-quarter scoring columns | ✅ Complete |
| 2024-11-XX | `migrate_add_ap_poll_rankings.py` | Add AP Poll rankings table for EPIC-010 | ✅ Complete |
| 2024-11-XX | `migrate_add_conference_name.py` | Add actual conference name field | ✅ Complete |
| 2024-11-XX | `migrate_add_game_type.py` | Add game type classification (EPIC-022) | ✅ Complete |
| 2024-12-XX | `migrate_add_transfer_portal_fields.py` | Add transfer portal metrics (EPIC-026) | ✅ Complete |

## Rollback

Currently, migrations do not have automatic rollback. To rollback:

1. Restore database from backup
2. Re-run migrations up to the point before the problematic migration

## Future: Alembic

For more robust migration management, consider migrating to Alembic:
- Automatic migration generation
- Up/down migrations
- Version tracking
- Conflict detection

See: https://alembic.sqlalchemy.org/

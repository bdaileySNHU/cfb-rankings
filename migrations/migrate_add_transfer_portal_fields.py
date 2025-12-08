"""
Add transfer portal fields to teams table
EPIC-026: Transfer Portal Team Rankings - Phase 1

This migration adds 3 new columns to store transfer portal metrics:
- transfer_portal_points: Total star points from incoming transfers
- transfer_portal_rank: National ranking (1 = best, 999 = N/A)
- transfer_count: Number of incoming transfers
"""

import sqlite3
import sys


def migrate():
    """Add transfer portal columns to teams table"""
    try:
        # Connect to database
        conn = sqlite3.connect('cfb_rankings.db')
        cursor = conn.cursor()

        print("=" * 80)
        print("MIGRATION: Add transfer portal fields")
        print("EPIC-026: Transfer Portal Team Rankings - Phase 1")
        print("=" * 80)
        print()

        # Add transfer portal columns
        columns_to_add = [
            ('transfer_portal_points', 'INTEGER DEFAULT 0'),
            ('transfer_portal_rank', 'INTEGER DEFAULT 999'),
            ('transfer_count', 'INTEGER DEFAULT 0'),
        ]

        for col_name, col_type in columns_to_add:
            print(f"Adding {col_name} column...")
            try:
                cursor.execute(f"ALTER TABLE teams ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️  Column '{col_name}' already exists - skipping")
                else:
                    raise

        print()

        # Commit changes
        conn.commit()

        # Verify columns added
        print("Verifying migration...")
        cursor.execute("PRAGMA table_info(teams)")
        columns = cursor.fetchall()
        portal_cols = [col for col in columns if 'transfer_portal' in col[1] or col[1] == 'transfer_count']
        print(f"✓ Verification: {len(portal_cols)} transfer portal columns in teams table")

        # Show default values
        cursor.execute("SELECT COUNT(*) FROM teams")
        team_count = cursor.fetchone()[0]
        if team_count > 0:
            print(f"✓ {team_count} existing teams will have default values:")
            print(f"  - transfer_portal_points: 0")
            print(f"  - transfer_portal_rank: 999 (N/A)")
            print(f"  - transfer_count: 0")

        conn.close()

        print()
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Re-import data to populate transfer portal metrics")
        print("     Command: python3 import_real_data.py")
        print("  2. The import will automatically:")
        print("     - Fetch transfer portal data from CFBD API")
        print("     - Calculate star-based rankings")
        print("     - Update all teams with portal metrics")
        print()
        print("Note: Old 'transfer_rank' field is deprecated but kept for compatibility")
        print()

        return 0

    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = migrate()
    sys.exit(exit_code)

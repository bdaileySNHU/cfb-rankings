"""
Database migration script to add AP Poll Rankings table for EPIC-010

Adds the ap_poll_rankings table to store weekly AP Poll rankings
for comparison with ELO predictions.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.database import SessionLocal, engine
from src.models.models import APPollRanking, Base


def migrate():
    """Add ap_poll_rankings table to database"""
    print("Creating ap_poll_rankings table...")

    try:
        # Create only the ap_poll_rankings table
        APPollRanking.__table__.create(engine, checkfirst=True)
        print("✓ AP Poll Rankings table created successfully!")

        # Verify table exists
        db = SessionLocal()
        try:
            # Try a simple query
            count = db.query(APPollRanking).count()
            print(f"✓ Table verified - currently {count} rankings stored")
        except Exception as e:
            print(f"✗ Error verifying table: {e}")
            return False
        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ Error creating ap_poll_rankings table: {e}")
        return False

if __name__ == "__main__":
    print("EPIC-010 Story 001: Adding AP Poll Rankings Table")
    print("=" * 60)

    success = migrate()

    if success:
        print("\nMigration completed successfully!")
        print("\nNext steps:")
        print("  1. Import AP Poll data: python3 import_real_data.py")
        print("  2. AP Poll rankings will be automatically fetched for each week")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)

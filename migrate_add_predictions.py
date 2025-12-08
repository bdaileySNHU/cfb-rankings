"""
Database migration script to add Predictions table for EPIC-009

Adds the predictions table to store pre-game predictions for accuracy tracking.
"""

import sys

from database import SessionLocal, engine
from models import Base, Prediction


def migrate():
    """Add predictions table to database"""
    print("Creating predictions table...")

    try:
        # Create only the predictions table
        Prediction.__table__.create(engine, checkfirst=True)
        print("✓ Predictions table created successfully!")

        # Verify table exists
        db = SessionLocal()
        try:
            # Try a simple query
            count = db.query(Prediction).count()
            print(f"✓ Table verified - currently {count} predictions stored")
        except Exception as e:
            print(f"✗ Error verifying table: {e}")
            return False
        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ Error creating predictions table: {e}")
        return False

if __name__ == "__main__":
    print("EPIC-009: Adding Predictions Table")
    print("=" * 60)

    success = migrate()

    if success:
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)

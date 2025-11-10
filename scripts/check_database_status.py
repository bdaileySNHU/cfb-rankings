#!/usr/bin/env python3
"""
Database Status Checker

Quick diagnostic script to check the current state of the CFB rankings database.
Useful for troubleshooting weekly updates and understanding data state.

Usage:
    python3 scripts/check_database_status.py
"""

import sqlite3
import sys
from pathlib import Path

# Get database path
project_root = Path(__file__).parent.parent
db_path = project_root / "cfb_rankings.db"

if not db_path.exists():
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

print(f"Checking database: {db_path}")
print("=" * 80)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Season Info
    print("\n=== SEASON INFO ===")
    cursor.execute("SELECT year, current_week, is_active FROM seasons")
    seasons = cursor.fetchall()
    if seasons:
        for row in seasons:
            active_status = "ACTIVE" if row[2] else "INACTIVE"
            print(f"Year: {row[0]}, Current Week: {row[1]}, Status: {active_status}")
    else:
        print("No seasons found in database")

    # Get the active season for further queries
    cursor.execute("SELECT year FROM seasons WHERE is_active = 1")
    active_season_result = cursor.fetchone()

    if not active_season_result:
        print("\nWARNING: No active season found")
        conn.close()
        sys.exit(0)

    active_season = active_season_result[0]

    # Games Overview
    print(f"\n=== GAMES OVERVIEW (Season {active_season}) ===")

    cursor.execute(f"SELECT COUNT(*) FROM games WHERE season={active_season}")
    total_games = cursor.fetchone()[0]
    print(f"Total games: {total_games}")

    cursor.execute(f"SELECT COUNT(*) FROM games WHERE season={active_season} AND is_processed=1")
    completed_games = cursor.fetchone()[0]
    print(f"Completed games (processed): {completed_games}")

    cursor.execute(f"SELECT COUNT(*) FROM games WHERE season={active_season} AND is_processed=0")
    upcoming_games = cursor.fetchone()[0]
    print(f"Upcoming games (unprocessed): {upcoming_games}")

    # Games by Week
    print(f"\n=== GAMES BY WEEK (Season {active_season}) ===")
    cursor.execute(f"""
        SELECT
            week,
            COUNT(*) as total,
            SUM(CASE WHEN is_processed=1 THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN is_processed=0 THEN 1 ELSE 0 END) as upcoming
        FROM games
        WHERE season={active_season}
        GROUP BY week
        ORDER BY week
    """)

    week_data = cursor.fetchall()
    if week_data:
        print(f"{'Week':<6} {'Total':<8} {'Completed':<12} {'Upcoming':<10}")
        print("-" * 40)
        for row in week_data:
            week, total, completed, upcoming = row
            print(f"{week:<6} {total:<8} {completed:<12} {upcoming:<10}")
    else:
        print("No games found")

    # Teams Count
    print(f"\n=== TEAMS ===")
    cursor.execute("SELECT COUNT(*) FROM teams")
    team_count = cursor.fetchone()[0]
    print(f"Total teams: {team_count}")

    # Predictions Count
    print(f"\n=== PREDICTIONS ===")
    cursor.execute(f"SELECT COUNT(*) FROM predictions WHERE season={active_season}")
    prediction_count = cursor.fetchone()[0]
    print(f"Total predictions for season {active_season}: {prediction_count}")

    # Weekly Update Status
    print(f"\n=== WEEKLY UPDATE STATUS ===")
    cursor.execute("SELECT COUNT(*) FROM update_tasks")
    task_count = cursor.fetchone()[0]

    if task_count > 0:
        cursor.execute("""
            SELECT task_id, status, trigger_type, started_at, completed_at
            FROM update_tasks
            ORDER BY started_at DESC
            LIMIT 5
        """)
        tasks = cursor.fetchall()
        print(f"Recent update tasks (last 5 of {task_count}):")
        print(f"{'Task ID':<25} {'Status':<12} {'Type':<10} {'Started':<20}")
        print("-" * 70)
        for task in tasks:
            task_id, status, trigger_type, started_at, completed_at = task
            print(f"{task_id:<25} {status:<12} {trigger_type:<10} {started_at:<20}")
    else:
        print("No update tasks found")

    conn.close()

    print("\n" + "=" * 80)
    print("Database check complete!")

except sqlite3.Error as e:
    print(f"\nDATABASE ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)

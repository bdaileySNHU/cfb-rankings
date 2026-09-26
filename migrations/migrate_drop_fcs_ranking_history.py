#!/usr/bin/env python3
"""Database Migration: Remove FCS rows from ranking_history

save_weekly_rankings() used to snapshot every team, so each week's rankings also
held the FCS placeholder opponents at rating 0. They padded the board to 200
rows and pulled the field average down to ~1090.

Deletes:
    - every row for a team that is still FCS
    - rows at rating 0, which are pre-promotion rows for schools that moved up
      from FCS (North Dakota State, Sacramento State in 2026). Left in, the
      board read their first real rating as a +1700 week-over-week swing.

No FBS team is ever rated 0. FCS rows could rank between FBS teams, so rank and
sos_rank are renumbered within each season/week afterwards, the same ordering
save_weekly_rankings() uses. Idempotent: safe to run multiple times.

Rollback: none needed; the rows were never meant to be there.
"""

import sqlite3
import sys

WHERE = "team_id IN (SELECT id FROM teams WHERE is_fcs = 1) OR elo_rating = 0"

# Dense 1..N within each season/week; ties keep their relative order by id.
RENUMBER = """
UPDATE ranking_history SET
    rank = (SELECT COUNT(*) + 1 FROM ranking_history r
            WHERE r.season = ranking_history.season AND r.week = ranking_history.week
              AND (r.elo_rating > ranking_history.elo_rating
                   OR (r.elo_rating = ranking_history.elo_rating AND r.id < ranking_history.id))),
    sos_rank = (SELECT COUNT(*) + 1 FROM ranking_history r
                WHERE r.season = ranking_history.season AND r.week = ranking_history.week
                  AND (r.sos > ranking_history.sos
                       OR (r.sos = ranking_history.sos AND r.id < ranking_history.id)))
"""


def migrate(db_path: str = "cfb_rankings.db") -> int:
    print("=" * 70)
    print("MIGRATION: Remove FCS rows from ranking_history")
    print("=" * 70)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        count = cur.execute(f"SELECT COUNT(*) FROM ranking_history WHERE {WHERE}").fetchone()[0]
        cur.execute(f"DELETE FROM ranking_history WHERE {WHERE}")
        cur.execute(RENUMBER)
        conn.commit()
        print(f"✓ Deleted {count} rows, renumbered rank and sos_rank")
        return 0
    except sqlite3.Error as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(migrate(sys.argv[1] if len(sys.argv) > 1 else "cfb_rankings.db"))

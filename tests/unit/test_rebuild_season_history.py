"""copy_back() is the only write the rebuild makes to the real database."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from rebuild_season_history import copy_back  # noqa: E402

SCHEMA = "CREATE TABLE ranking_history (id INTEGER PRIMARY KEY, team_id INT, season INT, week INT, elo_rating FLOAT)"


def _db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    conn.executemany("INSERT INTO ranking_history (team_id, season, week, elo_rating) VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_replaces_only_rebuilt_weeks(tmp_path):
    target, work = tmp_path / "target.db", tmp_path / "work.db"
    _db(target, [(1, 2025, 1, 2015.0), (1, 2025, 999, 2090.0), (1, 2026, 1, 1791.0)])
    _db(work, [(1, 2025, 0, 1684.0), (1, 2025, 1, 1701.0), (1, 2025, 999, 1.0)])

    assert copy_back(work, target, [2025]) == 2

    rows = sqlite3.connect(target).execute(
        "SELECT season, week, elo_rating FROM ranking_history ORDER BY season, week"
    ).fetchall()
    # Leaked week 1 replaced; 999 sentinel and other seasons untouched.
    assert rows == [(2025, 0, 1684.0), (2025, 1, 1701.0), (2025, 999, 2090.0), (2026, 1, 1791.0)]

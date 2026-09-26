"""The FCS cleanup migration drops FCS and rating-0 rows and closes the rank gaps."""

import sqlite3

from migrations.migrate_drop_fcs_ranking_history import migrate


def test_drops_fcs_rows_and_renumbers(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE teams (id INTEGER PRIMARY KEY, is_fcs BOOLEAN);
        CREATE TABLE ranking_history (id INTEGER PRIMARY KEY, team_id INT, season INT,
            week INT, rank INT, elo_rating FLOAT, sos FLOAT, sos_rank INT);
        INSERT INTO teams VALUES (1, 0), (2, 1), (3, 0), (4, 0);
        -- FCS team 2 ranked between FBS teams; team 4 is a promoted school's old 0 row
        INSERT INTO ranking_history VALUES
            (1, 1, 2026, 3, 1, 1800, 1500, 2),
            (2, 2, 2026, 3, 2, 1700, 1600, 1),
            (3, 3, 2026, 3, 3, 1600, 1400, 3),
            (4, 4, 2026, 3, 4, 0,    1300, 4);
    """)
    conn.commit()
    conn.close()

    assert migrate(str(db)) == 0
    assert migrate(str(db)) == 0  # idempotent

    rows = sqlite3.connect(db).execute(
        "SELECT team_id, rank, sos_rank FROM ranking_history ORDER BY rank").fetchall()
    assert rows == [(1, 1, 1), (3, 2, 2)]

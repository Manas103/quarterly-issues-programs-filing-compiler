"""SQLite schema and connection helper for the segment log.

One table. A segment is one aired piece of a weekly public-affairs show:
an air date, an air time, a duration in minutes, which of the 8 fixed
issue categories it addressed, and a short narrative describing what it
covered. Everything the compiler and the oracle need comes from this
one table; there is deliberately no normalization into an "episodes"
table because an issues-and-programs filing is a segment-level document,
not an episode-level one.
"""

from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    air_date        TEXT    NOT NULL,   -- ISO 'YYYY-MM-DD'
    air_time        TEXT    NOT NULL,   -- 'HH:MM'
    duration_min    INTEGER NOT NULL CHECK (duration_min > 0),
    category        TEXT    NOT NULL,
    narrative       TEXT    NOT NULL,
    quarter_year    INTEGER NOT NULL,
    quarter_number  INTEGER NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),
    episode_index   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_segments_quarter
    ON segments (quarter_year, quarter_number);

CREATE INDEX IF NOT EXISTS idx_segments_category
    ON segments (quarter_year, quarter_number, category);
"""


def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def clear_segments(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM segments")
    conn.commit()


def insert_segments(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO segments
            (air_date, air_time, duration_min, category, narrative,
             quarter_year, quarter_number, episode_index)
        VALUES
            (:air_date, :air_time, :duration_min, :category, :narrative,
             :quarter_year, :quarter_number, :episode_index)
        """,
        rows,
    )
    conn.commit()


def count_segments(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0]

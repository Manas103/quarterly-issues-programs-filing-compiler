"""The independent reference oracle: no SQL, no GROUP BY, no SUM().

This module is deliberately the slow, obviously-correct path: it pulls
every row as a plain tuple with a bare `SELECT *` (no WHERE, no
aggregation at all) and does every bit of filtering and summation in
pure Python with nested loops. It shares no aggregation code with
compiler.py; the only thing the two modules have in common is the
database file. compare.py diffs their outputs exactly, row for row and
total for total, across all 320 segments.
"""

from __future__ import annotations

import sqlite3

from qipc.categories import CATEGORIES
from qipc.deadlines import Quarter


def fetch_all_rows_unfiltered(conn: sqlite3.Connection) -> list[tuple]:
    """Every segment in the whole database, as plain tuples, no SQL filtering."""
    cur = conn.execute(
        "SELECT id, air_date, air_time, duration_min, category, narrative, "
        "quarter_year, quarter_number FROM segments"
    )
    return cur.fetchall()


def naive_category_totals(all_rows: list[tuple], q: Quarter) -> dict[str, int]:
    """Nested loop: for each category, scan every row and sum matches by hand.

    This is intentionally O(categories * rows) instead of one indexed
    GROUP BY, and it never calls sqlite3's SUM aggregate function.
    """
    totals: dict[str, int] = {}
    for category in CATEGORIES:
        running_total = 0
        for row in all_rows:
            (_id, _air_date, _air_time, duration_min, row_category,
             _narrative, quarter_year, quarter_number) = row
            if quarter_year != q.year:
                continue
            if quarter_number != q.quarter:
                continue
            if row_category != category:
                continue
            running_total = running_total + duration_min
        totals[category] = running_total
    return totals


def naive_quarter_total(all_rows: list[tuple], q: Quarter) -> int:
    """Plain accumulation, no SQL, no SUM(), no GROUP BY."""
    total = 0
    for row in all_rows:
        (_id, _air_date, _air_time, duration_min, _category,
         _narrative, quarter_year, quarter_number) = row
        if quarter_year == q.year and quarter_number == q.quarter:
            total += duration_min
    return total


def naive_segment_count(all_rows: list[tuple], q: Quarter) -> int:
    count = 0
    for row in all_rows:
        (_id, _air_date, _air_time, _duration_min, _category,
         _narrative, quarter_year, quarter_number) = row
        if quarter_year == q.year and quarter_number == q.quarter:
            count += 1
    return count

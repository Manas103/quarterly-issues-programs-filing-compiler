"""The SQL-aggregation compiler path.

Produces, for one quarter:
  (a) the full issues-and-programs list: every segment's air date, air
      time, duration and narrative, grouped by issue category, plus the
      statutory filing deadline for that quarter;
  (b) the least-airtime ranking: the 8 categories sorted ascending by
      total minutes aired, least-covered first.

All aggregation here goes through SQL (`GROUP BY` / `SUM`). The
independently-coded cross-check in naive_oracle.py recomputes the same
totals with no SQL at all, and compare.py diffs the two exactly.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from qipc.categories import CATEGORIES
from qipc.deadlines import Quarter


@dataclass
class SegmentRecord:
    id: int
    air_date: str
    air_time: str
    duration_min: int
    category: str
    narrative: str


@dataclass
class FilingList:
    quarter: Quarter
    filing_deadline: str
    segments_by_category: dict[str, list[SegmentRecord]]
    category_totals: dict[str, int]
    quarter_total: int

    @property
    def all_segments(self) -> list[SegmentRecord]:
        out: list[SegmentRecord] = []
        for cat in CATEGORIES:
            out.extend(self.segments_by_category.get(cat, []))
        return out


def fetch_segments_for_quarter(conn: sqlite3.Connection, q: Quarter) -> list[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT id, air_date, air_time, duration_min, category, narrative
        FROM segments
        WHERE quarter_year = ? AND quarter_number = ?
        ORDER BY category, air_date, air_time, id
        """,
        (q.year, q.quarter),
    )
    return cur.fetchall()


def category_totals_sql(conn: sqlite3.Connection, q: Quarter) -> dict[str, int]:
    """Per-category total airtime, computed by SQL GROUP BY / SUM."""
    cur = conn.execute(
        """
        SELECT category, SUM(duration_min) AS total_min
        FROM segments
        WHERE quarter_year = ? AND quarter_number = ?
        GROUP BY category
        """,
        (q.year, q.quarter),
    )
    totals = {row["category"]: row["total_min"] for row in cur.fetchall()}
    # Categories with zero segments in a quarter still belong in the
    # ranking at 0 minutes; none of the 8 are expected to be empty in
    # this synthetic log, but the filing should not silently drop one.
    for cat in CATEGORIES:
        totals.setdefault(cat, 0)
    return totals


def quarter_total_sql(conn: sqlite3.Connection, q: Quarter) -> int:
    row = conn.execute(
        """
        SELECT SUM(duration_min) AS total_min
        FROM segments
        WHERE quarter_year = ? AND quarter_number = ?
        """,
        (q.year, q.quarter),
    ).fetchone()
    return row["total_min"] or 0


def build_filing_list(conn: sqlite3.Connection, q: Quarter) -> FilingList:
    rows = fetch_segments_for_quarter(conn, q)
    by_category: dict[str, list[SegmentRecord]] = {cat: [] for cat in CATEGORIES}
    for row in rows:
        rec = SegmentRecord(
            id=row["id"],
            air_date=row["air_date"],
            air_time=row["air_time"],
            duration_min=row["duration_min"],
            category=row["category"],
            narrative=row["narrative"],
        )
        by_category[rec.category].append(rec)

    totals = category_totals_sql(conn, q)
    total = quarter_total_sql(conn, q)

    return FilingList(
        quarter=q,
        filing_deadline=q.filing_deadline().isoformat(),
        segments_by_category=by_category,
        category_totals=totals,
        quarter_total=total,
    )


def rank_categories_by_airtime(totals: dict[str, int]) -> list[tuple[str, int]]:
    """Ascending by total minutes (least-covered issue first).

    Ties broken alphabetically by category name so the ranking is a
    well-defined total order even if two categories ever land on the
    same total (the seeded data here is constructed so that does not
    happen; see tests/test_compiler.py::test_no_tied_category_totals).
    """
    return sorted(totals.items(), key=lambda kv: (kv[1], kv[0]))

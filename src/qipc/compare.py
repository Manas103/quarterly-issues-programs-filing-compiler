"""Diff the SQL compiler path against the independent naive oracle.

Runs both paths over all segments for a set of quarters and reports
every mismatch found, per category and per quarter total. A clean run
reports 0 mismatches across every category and every quarter; this
module does not shortcut past the first mismatch, so a genuine defect
in either path would show up as a nonzero count rather than an
exception that masks the rest of the comparison.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from qipc.categories import CATEGORIES
from qipc.compiler import category_totals_sql, quarter_total_sql
from qipc.deadlines import Quarter
from qipc.naive_oracle import (
    fetch_all_rows_unfiltered,
    naive_category_totals,
    naive_quarter_total,
    naive_segment_count,
)


@dataclass
class QuarterDiff:
    quarter: Quarter
    category_mismatches: list[tuple[str, int, int]] = field(default_factory=list)  # (cat, sql, naive)
    quarter_total_sql: int = 0
    quarter_total_naive: int = 0
    quarter_total_mismatch: bool = False
    segment_count_sql: int = 0
    segment_count_naive: int = 0
    segment_count_mismatch: bool = False

    @property
    def mismatch_count(self) -> int:
        return (
            len(self.category_mismatches)
            + (1 if self.quarter_total_mismatch else 0)
            + (1 if self.segment_count_mismatch else 0)
        )


def diff_quarter(conn: sqlite3.Connection, q: Quarter, all_rows: list[tuple]) -> QuarterDiff:
    sql_totals = category_totals_sql(conn, q)
    naive_totals = naive_category_totals(all_rows, q)

    mismatches = []
    for cat in CATEGORIES:
        sql_val = sql_totals.get(cat, 0)
        naive_val = naive_totals.get(cat, 0)
        if sql_val != naive_val:
            mismatches.append((cat, sql_val, naive_val))

    sql_q_total = quarter_total_sql(conn, q)
    naive_q_total = naive_quarter_total(all_rows, q)

    sql_count = sum(1 for _ in conn.execute(
        "SELECT 1 FROM segments WHERE quarter_year=? AND quarter_number=?",
        (q.year, q.quarter),
    ))
    naive_count = naive_segment_count(all_rows, q)

    return QuarterDiff(
        quarter=q,
        category_mismatches=mismatches,
        quarter_total_sql=sql_q_total,
        quarter_total_naive=naive_q_total,
        quarter_total_mismatch=(sql_q_total != naive_q_total),
        segment_count_sql=sql_count,
        segment_count_naive=naive_count,
        segment_count_mismatch=(sql_count != naive_count),
    )


def diff_all_quarters(conn: sqlite3.Connection, quarters: list[Quarter]) -> list[QuarterDiff]:
    all_rows = fetch_all_rows_unfiltered(conn)
    return [diff_quarter(conn, q, all_rows) for q in quarters]


def total_mismatches(diffs: list[QuarterDiff]) -> int:
    return sum(d.mismatch_count for d in diffs)


def format_diff_report(diffs: list[QuarterDiff]) -> str:
    lines = ["Independent recomputation diff report", "=" * 40]
    for d in diffs:
        lines.append(f"\n{d.quarter.label}:")
        lines.append(f"  segment count: sql={d.segment_count_sql} naive={d.segment_count_naive} "
                      f"match={not d.segment_count_mismatch}")
        lines.append(f"  quarter total: sql={d.quarter_total_sql} naive={d.quarter_total_naive} "
                      f"match={not d.quarter_total_mismatch}")
        lines.append(f"  category mismatches: {len(d.category_mismatches)}")
        for cat, sql_v, naive_v in d.category_mismatches:
            lines.append(f"    MISMATCH {cat}: sql={sql_v} naive={naive_v}")
    total = total_mismatches(diffs)
    lines.append(f"\nTOTAL MISMATCHES ACROSS ALL QUARTERS AND CATEGORIES: {total}")
    return "\n".join(lines)

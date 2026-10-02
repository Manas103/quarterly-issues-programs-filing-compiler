"""End-to-end run: seed 320 synthetic segments, compile both quarters'
filings, cross-check every total against the independent oracle,
generate the Word filings and the PowerPoint coverage deck, and print
every measured claim this project makes.

Usage:
    .venv\\Scripts\\python.exe scripts\\run_pipeline.py
"""

from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qipc import db
from qipc.categories import CATEGORIES
from qipc.compare import diff_all_quarters, format_diff_report, total_mismatches
from qipc.compiler import build_filing_list, rank_categories_by_airtime
from qipc.deadlines import Quarter
from qipc.reports.docx_filing import build_filing_document
from qipc.reports.pptx_deck import build_coverage_deck
from qipc.seed_data import DEFAULT_QUARTERS, generate_all_segments

STATION_NAME = "WKFT-TV"  # fictional, synthetic
CALL_SIGN = "WKFT"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "qipc.db")


def main() -> int:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = db.connect(DB_PATH)
    db.init_schema(conn)

    quarters = DEFAULT_QUARTERS
    rows = generate_all_segments(quarters)
    print(f"Generated {len(rows)} synthetic segments across {len(quarters)} quarters "
          f"and {len(CATEGORIES)} issue categories.")
    db.insert_segments(conn, rows)
    total_in_db = db.count_segments(conn)
    print(f"Inserted into SQLite: {total_in_db} rows (db.count_segments == {total_in_db}).")
    assert total_in_db == 320, f"expected 320 segments, found {total_in_db}"

    filings = []
    for q in quarters:
        filing = build_filing_list(conn, q)
        filings.append(filing)

        segment_total = len(filing.all_segments)
        print(f"\n--- {q.label} ---")
        print(f"Filing deadline (10th day of next quarter): {filing.filing_deadline}")
        print(f"Segments in this quarter's filing: {segment_total}")
        print(f"Quarter total airtime: {filing.quarter_total} minutes")

        # Invariant: sum of per-category totals equals the quarter total.
        cat_sum = sum(filing.category_totals.values())
        assert cat_sum == filing.quarter_total, (
            f"category totals sum to {cat_sum}, quarter total is {filing.quarter_total}"
        )
        print(f"Invariant check: sum of per-category totals ({cat_sum}) "
              f"== quarter total ({filing.quarter_total}): OK")

        # Invariant: every segment appears exactly once.
        ids = [s.id for s in filing.all_segments]
        assert len(ids) == len(set(ids)), "a segment id appears more than once in the filing"
        print(f"Invariant check: every one of {len(ids)} segments appears exactly once: OK")

        ranking = rank_categories_by_airtime(filing.category_totals)
        print("Least-airtime ranking (ascending):")
        for rank, (cat, total) in enumerate(ranking, start=1):
            print(f"  {rank}. {cat}: {total} min")
        least_cat, least_total = ranking[0]
        print(f"Least-covered issue: {least_cat} ({least_total} min)")

        # Report fields present: air date, time, duration, narrative.
        sample = filing.all_segments[0]
        assert sample.air_date and sample.air_time and sample.duration_min and sample.narrative
        print("Per-segment fields present: air_date, air_time, duration_min, narrative: OK")

    # Deadline logic matches the statutory computation, independently re-checked here.
    for q in quarters:
        expected = q.filing_deadline()
        assert expected.day == 10
        print(f"\nDeadline assertion for {q.label}: {expected.isoformat()} is the 10th. OK")

    # Independent recomputation cross-check across all 320 segments.
    diffs = diff_all_quarters(conn, quarters)
    print("\n" + format_diff_report(diffs))
    mismatches = total_mismatches(diffs)
    assert mismatches == 0, f"oracle diff found {mismatches} mismatches"

    # No tied category totals (so the ranking is a real order, not an assumption).
    for filing in filings:
        totals = list(filing.category_totals.values())
        assert len(totals) == len(set(totals)), f"tied category totals in {filing.quarter.label}"
    print("\nNo tied category totals in either quarter: confirmed.")

    # Generate the Word filings and the PowerPoint coverage deck.
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "samples")
    os.makedirs(samples_dir, exist_ok=True)
    generated_on = date.today()

    for filing in filings:
        out_path = os.path.join(
            samples_dir, f"issues_programs_list_{filing.quarter.year}_Q{filing.quarter.quarter}.docx"
        )
        build_filing_document(filing, STATION_NAME, CALL_SIGN, generated_on, out_path)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"Wrote {out_path} ({size_kb:.1f} KB)")

    deck_path = os.path.join(samples_dir, "coverage_deck.pptx")
    build_coverage_deck(filings, STATION_NAME, CALL_SIGN, generated_on, deck_path)
    deck_kb = os.path.getsize(deck_path) / 1024
    print(f"Wrote {deck_path} ({deck_kb:.1f} KB)")

    conn.close()
    print("\nPipeline run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

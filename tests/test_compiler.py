"""The SQL compiler path: filing list fields, deadline logic, ranking,
and the conservation invariants (every segment appears exactly once,
per-category totals sum to the quarter total)."""

import os
import sqlite3
import tempfile

import pytest

from qipc import db
from qipc.categories import CATEGORIES
from qipc.compiler import build_filing_list, rank_categories_by_airtime
from qipc.deadlines import Quarter
from qipc.seed_data import DEFAULT_QUARTERS, generate_all_segments


@pytest.fixture
def seeded_conn():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = db.connect(path)
    db.init_schema(conn)
    rows = generate_all_segments(DEFAULT_QUARTERS)
    db.insert_segments(conn, rows)
    yield conn
    conn.close()
    os.remove(path)


def test_filing_list_covers_every_segment_exactly_once(seeded_conn):
    for q in DEFAULT_QUARTERS:
        filing = build_filing_list(seeded_conn, q)
        ids = [s.id for s in filing.all_segments]
        assert len(ids) == len(set(ids)), "a segment id repeats in the filing"
        assert len(ids) == 160


def test_every_segment_carries_the_four_required_fields(seeded_conn):
    q = DEFAULT_QUARTERS[0]
    filing = build_filing_list(seeded_conn, q)
    for seg in filing.all_segments:
        assert seg.air_date
        assert seg.air_time
        assert isinstance(seg.duration_min, int) and seg.duration_min > 0
        assert seg.narrative


def test_filing_deadline_is_the_statutory_10th_of_next_quarter(seeded_conn):
    q = Quarter(2025, 4)
    filing = build_filing_list(seeded_conn, q)
    assert filing.filing_deadline == "2026-01-10"

    q2 = Quarter(2026, 1)
    filing2 = build_filing_list(seeded_conn, q2)
    assert filing2.filing_deadline == "2026-04-10"


def test_conservation_identity_category_totals_sum_to_quarter_total(seeded_conn):
    for q in DEFAULT_QUARTERS:
        filing = build_filing_list(seeded_conn, q)
        assert sum(filing.category_totals.values()) == filing.quarter_total


def test_ranking_covers_all_8_categories_ascending(seeded_conn):
    q = DEFAULT_QUARTERS[0]
    filing = build_filing_list(seeded_conn, q)
    ranking = rank_categories_by_airtime(filing.category_totals)
    assert len(ranking) == 8
    assert {c for c, _ in ranking} == set(CATEGORIES)
    totals = [t for _, t in ranking]
    assert totals == sorted(totals)  # strictly non-decreasing (ascending)


def test_no_tied_category_totals(seeded_conn):
    """The seeded data is constructed so no two categories tie; a tie would
    make the 'least airtime' claim an artifact of the tie-break rule
    instead of a real measurement."""
    for q in DEFAULT_QUARTERS:
        filing = build_filing_list(seeded_conn, q)
        totals = list(filing.category_totals.values())
        assert len(totals) == len(set(totals)), f"tied totals in {q.label}: {filing.category_totals}"


def test_ranking_tie_break_is_alphabetical_when_forced():
    """rank_categories_by_airtime itself still needs a defined tie-break,
    even though the seeded data never exercises it; tested directly here
    against an artificial tied input."""
    totals = {"Housing": 10, "Education": 10, "Health": 5}
    ranking = rank_categories_by_airtime(totals)
    assert ranking[0] == ("Health", 5)
    assert ranking[1] == ("Education", 10)
    assert ranking[2] == ("Housing", 10)

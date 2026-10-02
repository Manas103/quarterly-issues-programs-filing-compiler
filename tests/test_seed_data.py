"""320 synthetic segments across 2 quarters and 8 issue categories,
non-uniformly distributed so the least-airtime ranking is meaningful.
"""

from qipc.categories import CATEGORIES
from qipc.seed_data import DEFAULT_QUARTERS, generate_all_segments


def test_total_segment_count_is_320():
    rows = generate_all_segments(DEFAULT_QUARTERS)
    assert len(rows) == 320


def test_roughly_160_per_quarter():
    rows = generate_all_segments(DEFAULT_QUARTERS)
    for q in DEFAULT_QUARTERS:
        count = sum(1 for r in rows if r["quarter_year"] == q.year and r["quarter_number"] == q.quarter)
        assert 150 <= count <= 170, f"{q.label} has {count} segments, expected roughly 160"


def test_every_category_present_and_non_uniform_per_quarter():
    rows = generate_all_segments(DEFAULT_QUARTERS)
    for q in DEFAULT_QUARTERS:
        per_cat_counts = {}
        for r in rows:
            if r["quarter_year"] == q.year and r["quarter_number"] == q.quarter:
                per_cat_counts[r["category"]] = per_cat_counts.get(r["category"], 0) + 1
        assert set(per_cat_counts) == set(CATEGORIES)
        # non-uniform: not every category has the same count
        assert len(set(per_cat_counts.values())) > 1


def test_deterministic_across_runs():
    rows_a = generate_all_segments(DEFAULT_QUARTERS)
    rows_b = generate_all_segments(DEFAULT_QUARTERS)
    assert rows_a == rows_b


def test_every_segment_has_the_four_required_fields():
    rows = generate_all_segments(DEFAULT_QUARTERS)
    for r in rows:
        assert r["air_date"]
        assert r["air_time"]
        assert r["duration_min"] > 0
        assert r["narrative"]


def test_air_dates_fall_within_their_declared_quarter():
    rows = generate_all_segments(DEFAULT_QUARTERS)
    quarter_by_key = {(q.year, q.quarter): q for q in DEFAULT_QUARTERS}
    for r in rows:
        q = quarter_by_key[(r["quarter_year"], r["quarter_number"])]
        from datetime import date
        d = date.fromisoformat(r["air_date"])
        assert q.start_date <= d <= q.end_date
        assert d.weekday() == 6  # Sunday, the show's weekly air day

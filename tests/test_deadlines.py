"""Statutory filing deadline: the 10th day of the next calendar quarter.

47 CFR 73.3526's "10th day of the succeeding calendar quarter" is tested
against all four quarters, including the Q4 -> Q1-of-next-year wrap, which
is the edge case that broke the first implementation (see README Findings).
"""

from datetime import date

import pytest

from qipc.deadlines import Quarter


@pytest.mark.parametrize(
    "year,quarter,expected",
    [
        (2025, 1, date(2025, 4, 10)),   # Q1 Jan-Mar -> due Apr 10
        (2025, 2, date(2025, 7, 10)),   # Q2 Apr-Jun -> due Jul 10
        (2025, 3, date(2025, 10, 10)),  # Q3 Jul-Sep -> due Oct 10
        (2025, 4, date(2026, 1, 10)),   # Q4 Oct-Dec -> due Jan 10 NEXT YEAR
    ],
)
def test_filing_deadline_lands_on_the_10th_of_the_next_quarter(year, quarter, expected):
    q = Quarter(year, quarter)
    assert q.filing_deadline() == expected


def test_quarter_bounds():
    q1 = Quarter(2026, 1)
    assert q1.start_date == date(2026, 1, 1)
    assert q1.end_date == date(2026, 3, 31)

    q4 = Quarter(2025, 4)
    assert q4.start_date == date(2025, 10, 1)
    assert q4.end_date == date(2025, 12, 31)


def test_invalid_quarter_number_rejected():
    with pytest.raises(ValueError):
        Quarter(2026, 5)
    with pytest.raises(ValueError):
        Quarter(2026, 0)

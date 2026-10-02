"""Quarter boundaries and the statutory filing deadline.

47 CFR 73.3526 requires the quarterly issues and programs list to be
placed in the online public inspection file "by the 10th day of the
succeeding calendar quarter." A calendar quarter here is the ordinary
Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec split used on the station's own
license renewal paperwork, not a fiscal quarter.
"""

from __future__ import annotations

from datetime import date
from dataclasses import dataclass

_QUARTER_START_MONTH = {1: 1, 2: 4, 3: 7, 4: 10}
_QUARTER_END_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}
_DAYS_IN_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


@dataclass(frozen=True)
class Quarter:
    year: int
    quarter: int  # 1..4

    def __post_init__(self) -> None:
        if self.quarter not in (1, 2, 3, 4):
            raise ValueError(f"quarter must be 1-4, got {self.quarter}")

    @property
    def start_date(self) -> date:
        return date(self.year, _QUARTER_START_MONTH[self.quarter], 1)

    @property
    def end_date(self) -> date:
        end_month = _QUARTER_END_MONTH[self.quarter]
        return date(self.year, end_month, _DAYS_IN_MONTH[end_month])

    @property
    def label(self) -> str:
        return f"Q{self.quarter} {self.year}"

    def filing_deadline(self) -> date:
        """The 10th day of the next calendar quarter.

        The first version computed ``end_month + 1`` directly and raised
        ``ValueError: month must be in 1..12`` for Q4, where end_month is
        12. The fix rolls the quarter index over through 1..4 and only
        increments the year when quarter 4 wraps to quarter 1 of the next
        year; see README Findings for the discriminating test failure.
        """
        next_quarter = self.quarter + 1
        next_year = self.year
        if next_quarter > 4:
            next_quarter = 1
            next_year += 1
        next_quarter_start_month = _QUARTER_START_MONTH[next_quarter]
        return date(next_year, next_quarter_start_month, 10)

    def __str__(self) -> str:
        return self.label

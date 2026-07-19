"""Unit tests for recurrence expansion."""
from __future__ import annotations

from datetime import datetime

from app.models.enums import Recurrence
from app.services.recurrence import OCCURRENCE_COUNT, add_months, expand

START = datetime(2026, 1, 15, 14, 0)


class TestAddMonths:
    def test_simple(self):
        assert add_months(START, 1) == datetime(2026, 2, 15, 14, 0)

    def test_year_rollover(self):
        assert add_months(datetime(2026, 12, 10, 9, 0), 2) == datetime(2027, 2, 10, 9, 0)

    def test_day_clamped_to_short_month(self):
        # Jan 31 + 1 month -> Feb 28 (2026 is not a leap year)
        assert add_months(datetime(2026, 1, 31, 12, 0), 1) == datetime(2026, 2, 28, 12, 0)

    def test_leap_year(self):
        assert add_months(datetime(2028, 1, 31, 12, 0), 1) == datetime(2028, 2, 29, 12, 0)


class TestExpand:
    def test_weekly_count_and_spacing(self):
        dates = expand(START, Recurrence.WEEKLY, 4)
        assert len(dates) == 4
        assert (dates[1] - dates[0]).days == 7

    def test_monthly(self):
        dates = expand(START, Recurrence.MONTHLY, 3)
        assert [d.month for d in dates] == [1, 2, 3]

    def test_quarterly(self):
        dates = expand(START, Recurrence.QUARTERLY, 4)
        assert [d.month for d in dates] == [1, 4, 7, 10]

    def test_yearly(self):
        dates = expand(START, Recurrence.YEARLY, 3)
        assert [d.year for d in dates] == [2026, 2027, 2028]

    def test_none_recurrence_stays_single(self):
        assert expand(START, Recurrence.NONE, 8) == [START]

    def test_occurrence_counts_cover_about_two_years(self):
        assert OCCURRENCE_COUNT[Recurrence.WEEKLY] == 26
        assert OCCURRENCE_COUNT[Recurrence.MONTHLY] == 12
        assert OCCURRENCE_COUNT[Recurrence.QUARTERLY] == 8
        assert OCCURRENCE_COUNT[Recurrence.YEARLY] == 3

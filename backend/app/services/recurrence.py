"""Recurrence expansion for manually created event series.

Occurrences are materialized as concrete event rows at creation time (rather
than expanded at read time), so the calendar, dashboard, and signal engine
need no recurrence awareness at all.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from app.models.enums import Recurrence

# How many occurrences to materialize per frequency (~2 years of coverage).
OCCURRENCE_COUNT = {
    Recurrence.WEEKLY: 26,
    Recurrence.MONTHLY: 12,
    Recurrence.QUARTERLY: 8,
    Recurrence.YEARLY: 3,
}


def add_months(dt: datetime, months: int) -> datetime:
    """Shift by whole months, clamping the day to the target month's length."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def expand(start: datetime, recurrence: Recurrence, count: int) -> list[datetime]:
    """Return `count` occurrence dates, starting with `start` itself."""
    dates = [start]
    current = start
    for _ in range(count - 1):
        if recurrence == Recurrence.WEEKLY:
            current = current + timedelta(weeks=1)
        elif recurrence == Recurrence.MONTHLY:
            current = add_months(current, 1)
        elif recurrence == Recurrence.QUARTERLY:
            current = add_months(current, 3)
        elif recurrence == Recurrence.YEARLY:
            current = add_months(current, 12)
        else:
            break
        dates.append(current)
    return dates

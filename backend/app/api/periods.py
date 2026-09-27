"""How a request names a run of days: `start` and `end`, both plain dates (BRD E2).

Every endpoint that filters by date takes these two query parameters and turns
them into a `DateRange` here, so "from 10 to 24 July" is parsed, validated and
bounded once for the whole API.
"""

from datetime import date
from typing import Annotated

from fastapi import Query

from app.api.errors import InvalidPeriodError
from app.domain.periods import DateRange

Start = Annotated[date | None, Query(description="First day of the period, included")]
End = Annotated[date | None, Query(description="Last day of the period, included")]


def _range(start: date, end: date) -> DateRange:
    try:
        return DateRange(start, end)
    except ValueError as error:
        raise InvalidPeriodError(str(error)) from error


def optional_period(start: Start = None, end: End = None) -> DateRange | None:
    """A filter's date range, or None for all dates; refuses one bound without the other."""
    if start is None and end is None:
        return None
    if start is None or end is None:
        raise InvalidPeriodError("Give both start and end, or neither")
    return _range(start, end)


def required_period(
    start: Annotated[date, Query(description="First day of the period, included")],
    end: Annotated[date, Query(description="Last day of the period, included")],
) -> DateRange:
    """The date range a statistics request must name (BRD E1, E2)."""
    return _range(start, end)

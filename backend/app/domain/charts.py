"""The statistics chart, worked out on the server (BRD E6).

The client draws what it is given: every bar's height is already a share of a
round scale, and the scale's ticks are already chosen, so no presentation code
re-derives an aggregate or a maximum (F7.5).
"""

import uuid
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from app.domain.statistics import CategoryChange, CategoryStanding

CHART_CATEGORIES = 8
"""How many categories the chart draws, biggest first; the table lists the rest."""

TICKS = 4
"""Roughly how many steps the value axis is divided into."""

_NICE_STEPS = (Decimal(1), Decimal(2), Decimal("2.5"), Decimal(5), Decimal(10))


@dataclass(frozen=True)
class Bar:
    """One bar: a category's spend in one period, and its height as a percentage of the scale."""

    value: Decimal
    height: Decimal


@dataclass(frozen=True)
class BarGroup:
    """One category's bars side by side: `previous` is None without a comparison."""

    category_id: uuid.UUID | None
    name: str | None
    current: Bar
    previous: Bar | None


@dataclass(frozen=True)
class Chart:
    """A grouped bar chart of spend per category (BRD E6).

    `scale_max` is the round top of the value axis and `ticks` its gridlines,
    from 0 up to it. `hidden` counts the categories left to the table.
    """

    scale_max: Decimal
    ticks: list[Decimal]
    groups: list[BarGroup]
    hidden: int


def nice_scale(peak: Decimal) -> tuple[Decimal, list[Decimal]]:
    """A round top for an axis reaching `peak`, and its ticks: 742.60 gives 800 by 200.

    The step is 1, 2, 2.5 or 5 times a power of ten, so the gridlines fall on
    numbers a reader can use. A peak of zero or less still gives an axis of 0 to 1.
    """
    if peak <= 0:
        return Decimal(1), [Decimal(0), Decimal(1)]
    rough = peak / TICKS
    magnitude = Decimal(10) ** rough.adjusted()
    step = next(n * magnitude for n in _NICE_STEPS if n * magnitude >= rough)
    top = (peak / step).to_integral_value(rounding=ROUND_CEILING) * step
    ticks = [step * i for i in range(int(top / step) + 1)]
    return top.normalize() + 0, [t.normalize() + 0 for t in ticks]


def build_chart(
    categories: list[CategoryStanding], changes: list[CategoryChange] | None = None
) -> Chart:
    """The chart for a ranked breakdown, with the previous period beside it when compared.

    Draws the `CHART_CATEGORIES` biggest categories in ranking order (E4). A bar
    for a period of refunds is drawn at zero height rather than below the axis.
    """
    rows: list[tuple[CategoryStanding, Decimal | None]] = (
        [(c.standing, c.previous_total) for c in changes]
        if changes is not None
        else [(c, None) for c in categories]
    )
    shown = rows[:CHART_CATEGORIES]
    peak = max(
        [max(s.total, p or Decimal(0)) for s, p in shown] or [Decimal(0)],
    )
    top, ticks = nice_scale(peak)

    def bar(value: Decimal) -> Bar:
        height = max(value, Decimal(0)) / top * 100
        return Bar(value, height.quantize(Decimal("0.1")))

    groups = [
        BarGroup(s.category_id, s.name, bar(s.total), None if p is None else bar(p))
        for s, p in shown
    ]
    return Chart(top, ticks, groups, hidden=len(rows) - len(shown))

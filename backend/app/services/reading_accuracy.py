import uuid
from datetime import UTC, date, datetime

from app.domain.reading_accuracy import AccuracyReport, accuracy_report
from app.repository.receipt import ReceiptRepository


def last_months(today: date, count: int) -> list[date]:
    """The first days of the last `count` months up to `today`'s, oldest first."""
    months: list[date] = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(date(year, month, 1))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return months[::-1]


async def reading_accuracy(
    receipts: ReceiptRepository, user_id: uuid.UUID, today: date, months: int
) -> AccuracyReport:
    """How often the user's receipts read in the last `months` months needed correcting (F15.4).

    Months are UTC calendar months of the day each receipt was read, not the purchase.
    """
    span = last_months(today, months)
    since = datetime.combine(span[0], datetime.min.time(), tzinfo=UTC)
    return accuracy_report(await receipts.readings_since(user_id, since), span)

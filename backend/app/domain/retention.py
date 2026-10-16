"""How long files are kept (F17.9.3).

Storage deletes them by itself — lifecycle rules on the bucket, in
`infra/terraform/storage.tf`, which must say the same numbers — so the service only
needs to know when a file is gone, never to delete it.
"""

from datetime import date, datetime, timedelta

PHOTO_RETENTION = timedelta(days=90)
"""A receipt's photos are kept this long after upload; the figures read from them stay."""
EXPORT_RETENTION = timedelta(days=7)
"""An export file is kept this long after it is written."""


def photos_kept_until(uploaded_at: datetime) -> date:
    """The last day a receipt's photos are still in storage."""
    return (uploaded_at + PHOTO_RETENTION).date()


def photos_removed(uploaded_at: datetime, has_photos: bool, today: date) -> bool:
    """Whether storage has removed this receipt's photos by `today`.

    A receipt with no photos — typed in, or forwarded as text — had nothing to remove.
    """
    return has_photos and today > photos_kept_until(uploaded_at)

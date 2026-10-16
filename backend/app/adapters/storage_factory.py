"""The configured object storage, for code that runs outside a request (ADR-0014)."""

from app.adapters.gcs_storage import GcsStorageService
from app.core.config import get_settings
from app.services.storage import S3StorageService


def configured_storage() -> S3StorageService | GcsStorageService:
    """A storage client for the deployment's backend, not yet opened: use `async with`.

    Cloud Storage in production, S3-compatible (MinIO) locally. Background work —
    writing an export, removing a deleted account's files — opens its own, since the
    request's client is closed by then.
    """
    settings = get_settings()
    if settings.storage_backend == "gcs":
        return GcsStorageService(settings)
    return S3StorageService(settings)

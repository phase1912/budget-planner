from app.models.upload_job import UploadJob
from tests.factories.base import ModelFactory


class UploadJobFactory(ModelFactory[UploadJob]):
    __model__ = UploadJob

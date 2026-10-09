from app.models.receipt import ReceiptChannel
from app.models.upload_job import UploadJob
from tests.factories.base import ModelFactory


class UploadJobFactory(ModelFactory[UploadJob]):
    __model__ = UploadJob

    # The upload wizard is the photo channel's; a random channel would make the
    # receipts a test stores come from anywhere (F11.1.4).
    channel = ReceiptChannel.PHOTO

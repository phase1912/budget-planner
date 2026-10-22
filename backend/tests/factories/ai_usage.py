from decimal import Decimal

from app.agent.metering import Purpose
from app.models.ai_usage import AiUsage
from tests.factories.base import ModelFactory


class AiUsageFactory(ModelFactory[AiUsage]):
    __model__ = AiUsage

    # A receipt read charged to its user, unless a test says otherwise (F21.9.1).
    purpose = Purpose.RECEIPT
    model = "vertex_ai/gemini-2.5-flash"
    input_tokens = 5000
    output_tokens = 2000
    audio_seconds = Decimal(0)
    credits = Decimal("10")
    charged = True

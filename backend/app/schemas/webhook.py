from pydantic import BaseModel


class InboundEmailResponse(BaseModel):
    """What the relay is told about one message; it never retries either answer.

    `reason` is set only when the message was dropped.
    """

    status: str
    reason: str | None = None

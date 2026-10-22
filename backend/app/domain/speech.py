"""What a recording from the microphone is (F21.2.2, F21.9.4)."""

import struct
from decimal import Decimal

MAX_SECONDS = Decimal(60)
"""The longest recording: recognised in one call, and bounded in what it costs."""


class NotWav(ValueError):
    """The bytes are not a PCM WAV the microphone makes."""


def wav_seconds(data: bytes) -> Decimal:
    """How long a WAV recording is, by its header: its data's size over its byte rate.

    Measured, never taken from the file's size, so a compressed hour cannot pass for a
    minute. Raises NotWav for anything else.
    """
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise NotWav("not a WAV recording")
    byte_rate = 0
    at = 12
    while at + 8 <= len(data):
        chunk, size = data[at : at + 4], struct.unpack("<I", data[at + 4 : at + 8])[0]
        if chunk == b"fmt " and size >= 12 and at + 20 <= len(data):
            byte_rate = struct.unpack("<I", data[at + 16 : at + 20])[0]
        elif chunk == b"data":
            if not byte_rate:
                break
            # A recording cut short says more data than it holds: what is there counts.
            held = min(size, len(data) - at - 8)
            return (Decimal(held) / byte_rate).quantize(Decimal("0.01"))
        at += 8 + size + (size % 2)
    raise NotWav("a WAV recording without its format or data")

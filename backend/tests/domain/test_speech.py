"""A recording's length, by its header (F21.9.4)."""

from decimal import Decimal

import pytest

from app.domain.speech import NotWav, wav_seconds
from tests.assistant.test_understanding import wav


def test_a_recording_is_as_long_as_its_data_over_its_byte_rate() -> None:
    assert wav_seconds(wav(2.5)) == Decimal("2.50")


def test_a_recording_cut_short_counts_what_it_holds() -> None:
    assert wav_seconds(wav(10)[: 44 + 32000]) == Decimal("1.00")


@pytest.mark.parametrize("data", [b"", b"RIFF", b"ID3\x04" + bytes(100), wav(1)[:20]])
def test_anything_but_a_wav_is_refused(data: bytes) -> None:
    with pytest.raises(NotWav):
        wav_seconds(data)

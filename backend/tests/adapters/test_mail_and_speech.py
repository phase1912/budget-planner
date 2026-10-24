"""Tests for DNS mail-domain resolution, outgoing mail relay and speech adapters."""

from unittest.mock import AsyncMock, MagicMock, patch

import dns.exception
import dns.resolver
import httpx
import pytest

from app.adapters.dns_mail_domains import DnsMailDomainResolver
from app.adapters.outgoing_mail import AppEngineMailSender, LogMailSender
from app.adapters.speech import ChirpSpeechAdapter, ModelSpeechAdapter, _host, _words
from app.agent.core import Agent, AgentError
from app.ports.email import EmailSendError, Letter
from app.ports.speech import SpeechUnavailable


@pytest.mark.asyncio
async def test_dns_resolver_returns_true_when_mx_record_exists() -> None:
    """A domain with an MX record receives mail (F17.8.4)."""
    resolver = DnsMailDomainResolver(timeout=1.0)
    with patch("dns.asyncresolver.resolve", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = MagicMock()
        assert await resolver.receives_mail("example.com") is True


@pytest.mark.asyncio
async def test_dns_resolver_returns_false_on_nxdomain() -> None:
    """A non-existent domain returns False immediately."""
    resolver = DnsMailDomainResolver(timeout=1.0)
    with patch(
        "dns.asyncresolver.resolve",
        new_callable=AsyncMock,
        side_effect=dns.resolver.NXDOMAIN,
    ):
        assert await resolver.receives_mail("invalid.example") is False


@pytest.mark.asyncio
async def test_dns_resolver_falls_back_through_records_and_handles_errors() -> None:
    """NoAnswer continues to A/AAAA; general DNSException returns None (undecided)."""
    resolver = DnsMailDomainResolver(timeout=1.0)
    with patch(
        "dns.asyncresolver.resolve",
        new_callable=AsyncMock,
        side_effect=dns.resolver.NoAnswer,
    ):
        assert await resolver.receives_mail("no-records.example") is False

    with patch(
        "dns.asyncresolver.resolve",
        new_callable=AsyncMock,
        side_effect=dns.exception.Timeout,
    ):
        assert await resolver.receives_mail("timeout.example") is None


@pytest.mark.asyncio
async def test_app_engine_mail_sender_posts_letter_and_handles_failures() -> None:
    """AppEngineMailSender posts to the relay and raises EmailSendError on HTTP failure."""
    sender = AppEngineMailSender(url="http://relay/send", secret="sec")
    letter = Letter(to="u@example.com", subject="Hi", body="Body", reply_to="r@example.com")

    ok_response = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok_response):
        await sender.send(letter)

    err_response = MagicMock(status_code=500)
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=err_response),
        pytest.raises(EmailSendError, match="500"),
    ):
        await sender.send(letter)

    with (
        patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("boom"),
        ),
        pytest.raises(EmailSendError, match="unreachable"),
    ):
        await sender.send(letter)


@pytest.mark.asyncio
async def test_log_mail_sender_logs_letter() -> None:
    """LogMailSender writes the letter to the warning log for local inspection."""
    sender = LogMailSender()
    await sender.send(Letter(to="u@example.com", subject="Sub", body="Body", reply_to="r@ex.com"))


def test_speech_helpers_format_host_and_words() -> None:
    """Regional endpoints prefix the host; transcripts join non-empty alternatives."""
    assert _host("global") == "speech.googleapis.com"
    assert _host("eu") == "eu-speech.googleapis.com"
    assert _words({"results": [{"alternatives": [{"transcript": " Привіт "}]}, {}]}) == "Привіт"


@pytest.mark.asyncio
async def test_model_speech_adapter_returns_transcript_and_handles_errors() -> None:
    """ModelSpeechAdapter returns trimmed words, empty string on empty content, or raises."""
    agent = MagicMock(spec=Agent)
    agent.run = AsyncMock(return_value="  Купив молоко  ")
    adapter = ModelSpeechAdapter(agent)

    assert await adapter.recognise(b"wav", "audio/wav", "uk") == "Купив молоко"

    agent.run = AsyncMock(side_effect=AgentError("empty content in response"))
    assert await adapter.recognise(b"wav", "audio/wav", "uk") == ""

    agent.run = AsyncMock(side_effect=AgentError("provider down"))
    with pytest.raises(SpeechUnavailable):
        await adapter.recognise(b"wav", "audio/wav", "uk")


@pytest.mark.asyncio
async def test_chirp_speech_adapter_recognises_and_records_usage() -> None:
    """ChirpSpeechAdapter calls the REST endpoint, records usage and extracts transcript."""
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 8000)
    wav_bytes = buf.getvalue()

    recorder = AsyncMock()
    adapter = ChirpSpeechAdapter(project="proj", location="eu", recorder=recorder)
    fake_creds = MagicMock(token="tok")
    ok_resp = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"results": [{"alternatives": [{"transcript": "Тест"}]}]}),
    )

    with (
        patch("google.auth.default", return_value=(fake_creds, "proj")),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok_resp),
    ):
        said = await adapter.recognise(wav_bytes, "audio/wav", "uk")

    assert said == "Тест"
    recorder.assert_awaited_once()

    bad_resp = MagicMock(status_code=503, text="unavailable")
    with (
        patch("google.auth.default", return_value=(fake_creds, "proj")),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=bad_resp),
        pytest.raises(SpeechUnavailable, match="503"),
    ):
        await adapter.recognise(b"wav", "audio/wav", "uk")

"""Speech recognised by Google Cloud (F21.2.2, ADR-0031): Speech-to-Text v2 with Chirp, or
the configured Gemini model hearing the recording itself.

Both take the WAV the browser records and keep nothing of it. Speech-to-Text is called over
its REST API with the runtime's own credentials, so no client library — and no gRPC — joins
the image.
"""

import asyncio
import base64
import logging
from typing import Any

from app.agent.core import Agent, AgentError
from app.agent.metering import Purpose, Recorder, spend
from app.agent.types import Message
from app.domain.quota import SPEECH_USD_PER_MINUTE
from app.domain.speech import wav_seconds
from app.ports.speech import SpeechUnavailable

logger = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class ChirpSpeechAdapter:
    """Speech-to-Text v2, the Chirp 3 model, telling the language by itself.

    Not told the user's language: people here speak Ukrainian, Polish and Russian in turn,
    and told "uk-UA" Chirp wrote a Polish sentence down as Ukrainian. Tried on 2026-10-22,
    Chirp 3 with "auto" got all three right — where Chirp 2 and Gemini misheard one — in
    about a second from the European endpoint.
    """

    def __init__(
        self,
        project: str,
        location: str,
        model: str = "chirp_3",
        recorder: Recorder | None = None,
    ) -> None:
        self.project = project
        self.location = location
        self.model = model
        self.recorder = recorder

    async def recognise(self, audio: bytes, mime_type: str, language: str) -> str:
        import google.auth
        import google.auth.transport.requests
        import httpx

        try:
            credentials: Any
            credentials, _ = google.auth.default(scopes=[SCOPE])
            # A token from the metadata server is a blocking request: off the event loop.
            await asyncio.to_thread(credentials.refresh, google.auth.transport.requests.Request())
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"https://{_host(self.location)}/v2/projects/"
                    f"{self.project}/locations/{self.location}/recognizers/_:recognize",
                    json={
                        "config": {
                            "autoDecodingConfig": {},
                            "model": self.model,
                            "languageCodes": ["auto"],
                        },
                        "content": base64.b64encode(audio).decode("ascii"),
                    },
                    headers={"Authorization": f"Bearer {credentials.token}"},
                )
        except Exception as exc:
            raise SpeechUnavailable(str(exc)) from exc
        if response.status_code != 200:
            logger.warning("Speech-to-Text answered %s: %s", response.status_code, response.text)
            raise SpeechUnavailable(f"Speech-to-Text answered {response.status_code}")
        if self.recorder is not None:
            seconds = wav_seconds(audio)
            await self.recorder(
                spend(
                    Purpose.SPEECH,
                    self.model,
                    seconds * SPEECH_USD_PER_MINUTE / 60,
                    audio_seconds=seconds,
                )
            )
        return _words(response.json())


def _host(location: str) -> str:
    return "speech.googleapis.com" if location == "global" else f"{location}-speech.googleapis.com"


def _words(answer: dict[str, Any]) -> str:
    return " ".join(
        str(r["alternatives"][0].get("transcript", "")).strip()
        for r in answer.get("results", [])
        if r.get("alternatives")
    ).strip()


class ModelSpeechAdapter:
    """The configured model hears the recording and writes down what was said.

    It is not told the user's language: told "most likely Ukrainian", it wrote a Polish
    sentence down in Ukrainian — and people here speak both.
    """

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def recognise(self, audio: bytes, mime_type: str, language: str) -> str:
        data = base64.b64encode(audio).decode("ascii")
        try:
            said = await self.agent.run(
                [
                    Message(
                        role="user",
                        content=[
                            {
                                "type": "text",
                                "text": "Write down exactly what is said in this recording, "
                                "in the language it is said in. Reply with the words only, "
                                "or nothing if nobody speaks.",
                            },
                            {
                                "type": "file",
                                "file": {"file_data": f"data:{mime_type};base64,{data}"},
                            },
                        ],
                    )
                ],
                max_tokens=500,
                purpose=Purpose.SPEECH,
            )
        except AgentError as exc:
            if "empty content" in str(exc):
                return ""
            raise SpeechUnavailable(str(exc)) from exc
        return said.strip()

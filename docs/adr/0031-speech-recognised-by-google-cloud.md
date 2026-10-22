# ADR 0031: Speech recognised by Google Cloud

**Date:** 2026-10-22
**Status:** Accepted — F21.2.2; replaces ADR-0025's "Speech is the browser's"

## Context

F21.2 gave the assistant a microphone through the browser's own speech recognition: free,
and no sound reached the service. In use it was too poor to keep. Ukrainian and Polish
came back garbled, Firefox has none, and each browser behaves differently. It was hidden
on 2026-10-20. Talking to the assistant is meant to be its main way in, so it needs a
recogniser that works the same everywhere and understands the product's languages.

## Decision

- **The browser records, the service recognises.** The microphone is recorded as a 16 kHz
  mono WAV, a minute at most, by an AudioWorklet. Every browser can make that format and
  every recogniser takes it. The recording goes to `POST /api/v1/assistant/speech`. The
  words come back into the text field, to send or correct. "Approve" said alone saves the
  waiting card.
- **Google Cloud behind our own port.** `SpeechPort` has two adapters:
  - Speech-to-Text v2 with the Chirp 3 model in the `eu` multi-region, telling the
    language by the sound ("auto"), called over REST with the runtime's own credentials,
    so no gRPC client joins the image;
  - the configured Gemini model hearing the recording itself.

  `SPEECH_ENGINE` chooses between them. Production uses Speech-to-Text. A deployment
  whose Speech-to-Text API is not enabled yet, and local work, use the model.
- **Nothing of the sound is kept.** The recording is read in memory, recognised and
  dropped. Only the words the user then sends become part of the conversation. The
  privacy policy says the recording goes to Google Cloud for recognition.
- **Bounded.** Recognition is rate-limited per client like a message. It joins the AI
  allowance when the two limits arrive (F21.9, ADR-0030).

## Consequences

- Cost:
  - Speech-to-Text gives 60 free minutes a month, then about 0.016 USD a minute;
  - the Gemini engine costs about 32 tokens a second of sound, a fraction of a cent per
    message.

  Both adapters were tried live on 2026-10-22 on the same synthetic Ukrainian, Polish and
  Russian phrases:
  - Chirp 3 with "auto" got all three right, with punctuation, in 1–2 seconds;
  - Chirp 2 and Gemini each misheard the first Ukrainian word.
- **The recogniser is never told the user's language.** People here switch between
  Ukrainian, Polish and Russian. Told "uk-UA", Chirp wrote a Polish sentence in
  Ukrainian, and Gemini did the same when hinted.
- The microphone needs a secure page (https or localhost); elsewhere it is not shown.
- Terraform enables `speech.googleapis.com` and grants the backend `roles/speech.client`.

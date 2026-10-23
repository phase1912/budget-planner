# ADR 0034: Asking before an account's data goes to the AI

**Date:** 2026-10-24
**Status:** Accepted — F25.3.2

## Context

App Review guideline 5.1.2(i) asks an app to say plainly, and to get explicit permission,
before personal data is shared with a third-party AI. Everything the service reads goes to
one: receipt photos, their lines and shops, what is said or written to the assistant, and
goals go to Google's Gemini on Vertex AI, recordings to Google Speech-to-Text. The privacy
policy said so, but nothing asked.

## Decision

- **An account allows it, with a date, or has not.** `users.ai_consent_at` holds when the owner
  allowed it; withdrawing clears it, and allowing again later sets a new date. Existing
  accounts start without it and are asked on their next visit — the service does not assume
  an agreement it never asked for.
- **One check, before every model call a user asks for.** `QuotaService.ensure_can_spend`,
  which every reading, message, recording, goal mapping and advice already passes through,
  refuses with `ai_consent_required` (403) first — admins included, as it is the owner's data.
  An emailed receipt is dropped with the reason `ai_not_allowed`, as one over the quota is.
- **Work nobody asked for asks the same.** The scheduled advice pass skips accounts without it,
  and product matching keeps product names away from the model, matching only by its rules.
- **Asked in one place, the same everywhere.** The client asks once signed in — what is sent, to
  whom, why, and that it can be withdrawn — on the website and in both store apps alike; a
  switch in Settings › Data withdraws or gives it again. Typing receipts and expenses by hand
  never needs it.

## Consequences

- Until an account allows it, uploading a photo, talking to the assistant and asking for advice
  answer with the reason instead of working.
- A new feature that calls a model must go through the wallet's check, or ask the same itself.

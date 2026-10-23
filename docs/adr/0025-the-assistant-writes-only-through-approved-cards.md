# ADR 0025: The assistant writes only through approved cards

**Date:** 2026-10-20
**Status:** Accepted — F21.1, F21.7; its "settings and the account have no tool" is replaced by ADR-0029

## Context

The assistant (E21) lets the user say what they want instead of finding the screen for it:
"raise the budget to 2 500", "salary came, 9 000 from Acme". A language model understands
such requests well but not perfectly. It may misread an amount, pick the wrong month or
make up something that was never said. Money figures that are quietly wrong break the
product's one promise: what it shows is true.

## Decision

- **The model never writes.** Every tool is either a read, which runs at once and answers
  from the user's own data, or a write, which only returns a **card**: the proposed action
  with its fields, looking like the screen it belongs to.
- **The user approves.** A card is saved only when the user approves it, by tapping or by
  saying "approve" (F21.7). They can change any field first, or dismiss it. Saving goes
  through the same service the screen calls, so ownership (N2), shared and child rules
  (F12.8, F12.10), closed months (F23.15) and every validation hold exactly as they do on
  the screens.
- **What has no tool cannot happen.** Settings and the account have no tool. (Deleting had
  none either until F21.7, ADR-0028: removing now goes through an approved card, as
  adding does.) A tool name the model invents is dropped. ADR-0029 (proposed, F21.11)
  narrows this to signing in: password, email, the second factor and deleting the account.
- **It costs the quota** below is replaced by one wallet of AI credits (ADR-0030, F21.9).
- **Provider-agnostic calling.** Tools are offered by description and called through
  structured output (`AssistantAdapter`), not a provider's own tool-calling, so every model
  the agent can reach — hosted or local — behaves the same.
  *Superseded by ADR-0032: tools are now the provider's own functions, which every model
  the agent reaches takes.*
- **It costs the quota.** Each message is a model call. Until credits by tokens arrive
  (F21.9), every started batch of `assistant_messages_per_read` messages (10) costs one
  receipt read.
- **Speech is the browser's.** Voice is turned into text by the browser's own recognition
  (free); no recording reaches this service, only the text. The browser's recogniser may
  run on its maker's servers — Chrome sends the sound to Google — which the privacy policy
  says before the microphone is first used.
  *Superseded by ADR-0031: the recording is recognised by Google Cloud.*

## Consequences

- A wrong understanding costs one tap to fix, never a wrong figure in the budget.
- The card's state (proposed, saved, dismissed) and what it created are kept with the
  conversation, so the history tells what was really done.
- Speech recognition depends on the browser. Chrome, Edge and Safari have it; Firefox does
  not, and there the microphone is not offered.
- Routing by intent across many write tools (F21.7.2) builds on this protocol unchanged.

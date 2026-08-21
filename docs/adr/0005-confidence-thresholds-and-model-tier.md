# ADR-0005 — Initial confidence thresholds and per-environment Claude model tier

- **Status:** Accepted
- **Date:** 2026-08-21

## Context

`docs/architecture/domain-model.md`'s Open decisions table has carried "Confidence
thresholds for OCR, categorisation and manual-review triggers" since F0.8.1, blocking
E3 and E5. The BRD (section 10) says the business will set these "in collaboration with
the development team during design" and leaves it as open question 14.5 — it does not
promise numbers, only a process. F0.7 (configuration, secrets and environments) is that
design moment: it needs a concrete default in `app.config.Settings` before E3/E5 can be
built against anything, so guessing cannot be deferred further.

A related decision was open by omission rather than by name: which Claude model tier
each environment calls. Nothing in the BRD fixes this — it is a cost/accuracy
trade-off the codebase has to make somewhere, and `app.config.Settings` (F0.7.1) is
where every other per-environment tunable already lives.

## Decision

### Confidence thresholds

| Setting | Default | Requirement |
|---|---|---|
| `ocr_confidence_threshold` | `0.80` | BRD A10 — below this, a required extracted field is flagged "low confidence" instead of accepted silently |
| `categorization_confidence_threshold` | `0.70` | BRD C3 — below this, a line item is `Uncategorized` and flagged for review instead of guessed |

These *are* the manual-review triggers the domain model's open-decisions row named
separately — BRD A10 and C3 describe the same event ("falls below a threshold" →
"flag for review") from the extraction side and the categorisation side respectively.
There is no third, independent "manual review" number.

Categorisation is set ten points lower than OCR because a wrong category is a cheap,
reversible mistake — the item is filed under "Uncategorized" and a user correction
teaches the categoriser (C4, C5) — while a wrong OCR field silently corrupts the
month's totals with no correction step until the user notices. The two are asymmetric
risks, so they get asymmetric thresholds.

Both are indicative starting points, not measured ones — there is no extraction or
categorisation model running against real receipts yet to measure precision/recall
against. BRD success criteria (section 12) leave "acceptable manual-review rate" open
(open question 14.1) for the same reason. **Revisit both once E3/E5 have real accuracy
data**; until then these are what `app.config.Settings` enforces and what E3/E5 build
their manual-review branch against.

### Per-environment Claude model tier

| Environment | `ANTHROPIC_MODEL` | Why |
|---|---|---|
| local | `claude-haiku-4-5-20251001` (default) | Cheapest, fastest — iteration speed matters more than extraction accuracy while developing against synthetic receipts |
| staging | `claude-haiku-4-5-20251001` (default) | Same tier as local: staging exists to catch integration and deployment defects, not to validate extraction accuracy, and inherits the default rather than needing its own opinion |
| production | `claude-sonnet-5` (set explicitly) | Real users' financial figures depend on extraction/categorisation accuracy — Sonnet trades some cost for materially better accuracy than Haiku; Opus was considered and rejected at this stage as more cost than the product's accuracy bar currently justifies |

`Settings.anthropic_model` (`app/config.py`) defaults to the local/staging tier rather
than branching on `environment` internally, so the model a deployment actually calls is
a visible `ANTHROPIC_MODEL` environment variable at that deployment, not implicit
behaviour buried in application code — consistent with how every other per-environment
value in this system is set (see `docs/architecture/environments.md`).

## Consequences

- `docs/architecture/domain-model.md`'s Open decisions row for confidence thresholds is
  resolved by this ADR; E3 and E5 are unblocked and must implement their manual-review
  branch against `Settings.ocr_confidence_threshold` /
  `Settings.categorization_confidence_threshold`, not a hardcoded number.
- `docs/architecture/configuration.md` documents both settings' purpose, default and
  bounds; `docs/architecture/environments.md` documents which `ANTHROPIC_MODEL` each
  tier sets.
- Changing either threshold, or a tier's model, is a config change (an env var), never
  a code change — no PR should hardcode a threshold or model id outside `app/config.py`.
- These numbers are provisional by design. When E3/E5 ship telemetry on real
  extraction/categorisation confidence, revisit this ADR rather than silently drifting
  the default in an unrelated PR.

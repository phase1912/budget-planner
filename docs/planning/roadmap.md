# Roadmap

Epic sequencing and what forces that order. Sizes are relative, not calendar estimates.

## Dependency graph

```
E0 Foundation ──┬─► E1 Identity ──┬─► E2 Ingestion ──► E3 Parsing ──┬─► E4 Position matching
                │                 │                                 │
                └─► E9 Web client │                                 └─► E5 Categorization
                                  │                                          │
                                  │                                          ▼
                                  │                                  E6 Monthly budget
                                  │                                          │
                                  │                                          ▼
                                  │                                  E7 Statistics ──► E8 Goals & advice
                                  │
                                  └─► E10 Security & observability (runs alongside, from E2 onward)
```

## Phases

### Phase 1 — Walking skeleton
**E0, E1, E9.** Both runtimes, database, migrations, CI, the BDD harness fed by the BRD's own
Gherkin, authentication, and the React/MobX conventions. Nothing here is visible to a user,
and skipping it is how a project ends up with six different opinions about state management.

**Done when:** a user can register, log in, and see an empty dashboard, with the whole path
covered by tests running in CI.

### Phase 2 — Receipts become data
**E2, E3.** The core loop: photograph a receipt, get back a structured record. This is where
the product's central technical risk lives — extraction quality — so it comes early, while
there is still room to change approach.

**Done when:** a photographed receipt appears as a correct, itemised record, with
low-confidence fields flagged rather than silently accepted.

### Phase 3 — Data becomes trustworthy
**E4, E5.** Position matching stops long receipts being double-counted; categorisation makes
the numbers mean something. Both feed on user corrections, so both need their correction paths
built, not deferred.

**Done when:** a two-photo receipt counts each item once, and items land in categories the
user agrees with — or can fix in one action.

### Phase 4 — Data becomes insight
**E6, E7.** Monthly totals, category breakdowns, comparison across periods, export.
The first point at which the product is genuinely useful without the AI advice layer.

**Done when:** the user can answer "where did my money go last month, and how does that
compare to the month before?"

### Phase 5 — Insight becomes advice
**E8.** The differentiator, and deliberately last: BRD F5 forbids advice on thin history, so
this feature is not testable until real spending data exists to reason over.

**Done when:** a stated goal produces specific, quantified recommendations citing the user's
own purchases, and a goal at risk raises a warning before the month ends.

### Continuous — E10
Security and observability start in Phase 2, when the first financial data is stored, and
continue throughout. The access-control test suite grows with every epic that introduces a
new user-owned entity.

## Risks that shape the sequence

| Risk | Why it moves work earlier |
|---|---|
| Extraction accuracy is unknown until tried on real receipts | E3 sits in Phase 2, not Phase 4 — a wrong answer here invalidates everything downstream |
| Position matching is easy to get subtly wrong (BRD B9: repeat purchases are not duplicates) | E4 gets its own epic instead of being a footnote inside parsing |
| Advice quality cannot be judged without history | E8 is last by necessity, not by preference |
| Encryption at rest retrofitted onto stored data is painful | E10 starts as soon as data storage does |

## Open questions blocking later phases

BRD section 14 leaves six questions open. Three of them block implementation and need answers
before their epic starts:

- **Confidence thresholds** (OCR, categorisation, manual review) — blocks E3 and E5.
- **Advice on limited data** — whether to withhold entirely or soften. Blocks E8.
- **Budget periods** — strict calendar months or custom cycles. Blocks E6.

The remaining three (success metric targets, launch currencies, household budgets) affect
scope beyond this phase and can be answered later.

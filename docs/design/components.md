# Component anatomy

The numbers behind each primitive, so "that button is wrong" is a checkable claim rather
than a matter of taste. Values live in `design.css`; this file says what they add up to
and when to reach for which.

Token names are used throughout. A component that hardcodes `#15803d` instead of
`var(--color-primary)` is wrong even when the pixels match, because the dark theme will
not follow it.

## Button

`.btn` plus one variant. Height comes from padding, never a fixed `height`.

| | Value |
|---|---|
| Radius | `--radius-control` (12px) |
| Padding | 10px 16px; `--compact` 9px 14px; `--lg` 13px 22px; `--sm` 8px 13px |
| Type | 14px / 600, inherits the body stack; `--sm` 13px |
| Icon | 16px, stroke 2, 8px gap before the label |
| Touch | ≥44px tall on mobile — enforced by `.screen--mobile .btn` |

| Variant | Background | Text | Border | Shadow |
|---|---|---|---|---|
| `--primary` | `--color-primary` | `--color-primary-foreground` | none | `--shadow-primary` |
| `--primary:hover` | `--color-primary-hover` | | | |
| `--secondary` | `--color-background` | `--color-foreground` | `--color-border` | none |
| `--ghost` | transparent | `--color-muted-foreground` | none | none |
| `--danger` | `--tone-error-bg` | `--tone-error-text` | `--tone-error-border` | none |
| `--danger-solid` | `--color-error` | white | none | none |
| `[disabled]` | unchanged | | | opacity .45 |

One primary button per view. Two competing primaries means the screen has not decided
what it is for.

## Input

`.input`, optionally inside `.input-group` when it carries an icon, a suffix or an action.

| | Value |
|---|---|
| Radius | `--radius-control` (12px) |
| Padding | 11px 12px; `+24px` on any side carrying an icon, action or suffix |
| Border | 1px `--color-border` |
| Type | 14px / 400 |
| Focus | border `--color-primary` + `--ring-primary` (3px, 20% alpha) |
| Invalid | border `--color-error`; message below in `.field__error`, 12px |
| Locked | background `--color-muted`, text `--color-muted-foreground` |

Every input has a real `<label>` — `.field__label`, 12px / 500, muted. Placeholder text is
not a label.

## Card

`.card` is the default container. `--surface` raises it off the page; `--flush` clips
children to the radius when the card holds rows or a table.

| | Value |
|---|---|
| Radius | `--radius-card` (16px) |
| Border | 1px `--color-border` |
| Background | `--color-background`; `--surface` uses `--color-surface` + `--shadow-card` |
| Padding | `.card__body` 22px 24px |
| Header | `.card__header` — surface fill, bottom hairline, 14px 18px |
| Footer | `.card__footer` — surface fill, top hairline, 13px 20px |

## Pill

`.pill` carries a business state, never decoration. Soft tone background, matching text.

| | Value |
|---|---|
| Radius | `--radius-pill` |
| Padding | 5px 11px; `--sm` 4px 10px |
| Type | 12px / 600 |
| Icon | 13px, stroke 2.5, 6px gap |

Tones: `--success`, `--warning`, `--error`, `--info`, `--accent`, and the bare neutral.
The vocabulary itself — Parsed, Low confidence, Requires review, Uncategorized,
Month-to-date, Finalised — is on `screens/design-language.html` and comes from the BRD.

## Banner

`.note` is a full-width strip explaining a state the user must know about. Tone carries
the meaning: **warning** holds something back, **error** blocks, **info** merely informs,
**success** confirms.

| | Value |
|---|---|
| Radius | `--radius-control` |
| Padding | 13px 16px |
| Type | 13px / 1.5 |
| Icon | 18px in `--*-text`, `flex-shrink: 0` |

A banner that says something is excluded must also say how much and offer the way to fix
it — that is BRD D3, not a style preference.

## Table and rows

Listings are CSS grid, not `<table>`, except where a real tabular comparison earns it
(statistics). Column widths live in the screen's own file.

| | Value |
|---|---|
| Header cell | `.th` — 11px / 600, uppercase, 0.05em tracking, muted |
| Body cell | `.td` — 13px |
| Row padding | 14px 18px in listings, 10–12px in dense tables |
| Divider | `.row` — 1px top border in `--color-muted`, never a full border |
| First row | `.row--head` — divider in `--color-border`, separating head from body |

Money, counts and dates carry `.num` (`tabular-nums`) so columns line up. Money is right
aligned; text is left aligned.

## Composite widgets

**Segmented control** (`.segmented`) — mutually exclusive modes. Muted trough, 4px inset,
the current option raised on `--color-background` with `--shadow-raised`. Use for two to
four options; more than that wants a select.

**Meter** (`.meter`) — 10px tall, 5px radius, fill in `--color-primary`. Past 100% the
fill takes `--fill--over` (`--color-error`) and the label says how far over. `--sm` is 5px
for secondary progress; `--track` is 8px on a muted trough for category bars, where the
fill takes the category colour.

**Stepper** (`.stepper`) — the upload wizard's three steps. A step is upcoming (bordered
marker, muted label), `--current` (primary fill) or `--done` (soft primary, check glyph);
the connector before a reached step turns primary.

**Modal** (`.overlay` + `.modal`) — the overlay is `rgba(0,0,0,0.6)` with a 4px blur; the
modal is a card with `--shadow-modal`. Header and footer sit on `--color-surface`. The
body scrolls, the frame does not.

**Menu** (`.menu`) — floating panel, 14px radius, `--shadow-pop`, 6px inset. Options are
9px 12px, 13px / 500; the selected option takes the soft primary tone and a check.

## Icons

Stroke-based on a 24px grid: `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`
(2.5 at 14px and below), round caps and joins. Rendered at 13, 15, 16, 18 or 22px
depending on context. Never an emoji, never a glyph font.

## Layout

- Content sits in `.app-container` — 1040px default, `--narrow` 880px for a single column
  of forms, `--wide` 1100px for the dashboard's two columns.
- Sibling groups use flex or grid with `gap`, never margins on children or whitespace
  between inline elements.
- Spacing steps from a 4px base: 4, 8, 12, 16, 24, 32, 48.
- Sections within a screen sit 20px apart; blocks inside a section 14–16px.

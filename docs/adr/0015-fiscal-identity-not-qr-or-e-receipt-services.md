# ADR 0015: A receipt is identified by its printed fiscal numbers, not by QR or e-receipt services

**Date:** 2026-10-09
**Status:** Accepted — the F11.4 spike

## Context

E11 planned two ways to get receipts without reading photos: scanning the fiscal QR code
to fetch the itemised receipt from the tax authority (F11.3), and integrating with the
national e-receipt services, e-Paragony in Poland and єЧек in Ukraine (F11.4). The spike
asked whether either is possible for a third-party app, in both markets.

**Ukraine.** A fiscal receipt's QR code is a link to the tax service's receipt search,
`cabinet.tax.gov.ua/cashregs/check?mac=…&date=yyyyMMdd&time=HHmm&id=…&sm=…&fn=…`
(Ministry of Finance order No. 13; the cabinet's API page). The page it opens shows the
electronic copy of the receipt, items included, without signing in. But the page is a web
application behind Google reCAPTCHA, and the cabinet's published API has no receipt
search: the items can be seen by a person, not fetched by a program. Getting round a
CAPTCHA is neither allowed nor durable.

**Poland.** Fiscal receipts from online cash registers carry no fiscal QR code. A QR code
on one is the shop's own — on a Rossmann receipt from 2026-09-14, the only QR code sits in
the non-fiscal part and links to the shop's app. The e-Paragony app verifies receipts,
but there is no public API for third parties; a standard has only been proposed.

**What every fiscal receipt does carry** is text that identifies it uniquely: in Poland
the cash register's unique number (`ECA 2201079960`) and the printout number
(`nr:85503`), plus an electronic signature; in Ukraine the register's fiscal number (ФН)
and the receipt's fiscal number.

Decoding QR codes on the photo was also tried: OpenCV's detectors, including the WeChat
one, could not read the code on a crumpled real receipt, and would add about 50 MB to the
backend image.

## Decision

- **No QR scanning and no e-receipt integration.** F11.3's QR intake and F11.4's
  integration are closed as not feasible for a third-party app today; this ADR records
  why, so they are not attempted again without new facts (a public API, a fiscal QR on
  Polish receipts).
- **The reader reads the fiscal identity off the photo**: the register number and the
  receipt number, normalised, as two fields of the extraction. A receipt without them
  (a restaurant bill, a non-fiscal printout, another country) simply has none.
- **The fiscal identity decides duplicates (F11.5).** A receipt whose register and receipt
  numbers match one the user already has is the same receipt — photographed twice, or
  photographed and emailed — and is not stored again; the wizard says so and when it was
  first added. Only receipts without a fiscal identity fall back to merchant, date and
  total (A14), which still asks the user, because two visits to one shop on one day are
  two purchases.

## Consequences

- Duplicate detection becomes exact for nearly every Polish and Ukrainian shop receipt,
  and across channels, at no cost: the model already reads the photo.
- The fiscal identity is only as good as the reading. A misread digit means a duplicate is
  missed — the fallback still catches most — never that two purchases are merged, since
  both numbers must match exactly.
- Should Poland adopt a public e-receipt API, it plugs in as another intake adapter
  (F11.1); the fiscal identity is then the key that joins its receipts to photographed ones.

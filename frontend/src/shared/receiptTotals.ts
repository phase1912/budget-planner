/** The most a receipt's lines may differ from its printed total and still agree: one grosz. */
export const TOTAL_TOLERANCE = 0.01;

/**
 * How a receipt's lines stand against its printed total (BRD A9), mirroring the
 * server's `lines_match_total`.
 *
 * `over` means the lines come to more than was paid: usually a discount the reader
 * missed, worth `gap`. `under` means they come to less: a line missing or misread.
 */
export type TotalsGap =
  { kind: "match" } | { kind: "over"; gap: number } | { kind: "under"; gap: number };

export function totalsGap(linesSum: number, printedTotal: number): TotalsGap {
  // Rounded to cents first, so float slop in typed numbers never decides the case.
  const gap = Math.round((linesSum - printedTotal) * 100) / 100;
  if (Math.abs(gap) <= TOTAL_TOLERANCE) return { kind: "match" };
  return gap > 0 ? { kind: "over", gap } : { kind: "under", gap: -gap };
}

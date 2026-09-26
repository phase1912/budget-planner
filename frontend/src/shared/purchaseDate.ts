/**
 * When a receipt's items were bought, as the shop printed it.
 *
 * The server stores the till's wall-clock time labelled UTC (ADR-0009), so it is
 * read back in UTC: a receipt printed at 11:26 shows 11:26 whichever timezone the
 * browser is in. Formatting it in local time would move it by the browser's
 * offset, and near midnight onto the wrong day or even month.
 */
export function formatPurchase(iso: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("en-GB", { ...options, timeZone: "UTC" }).format(new Date(iso));
}

export interface YearMonth {
  year: number;
  month: number;
}

/** The budget month a purchase is counted in (BRD D1), read the same way as above. */
export function purchaseMonth(iso: string): YearMonth {
  const date = new Date(iso);
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1 };
}

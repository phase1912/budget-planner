import { numberFormat } from "@/i18n/format";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const CENTS = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** A sample amount as the app shows it, in the page's language and no currency (F17.11). */
export function sampleAmount(value: number): string {
  return value >= 100 ? WHOLE.format(value) : CENTS.format(value);
}

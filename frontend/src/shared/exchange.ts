/**
 * How a receipt in another currency was, or will be, converted into the account's
 * (F11.7, ADR-0016). Rate dates are calendar days, so they are formatted in UTC.
 */

export interface RateNote {
  rate: string;
  rateDate: string;
  source: string;
}

function day(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(iso));
}

/** "NBP rate, 2 October", or "converted by you" for a rate the owner typed amounts at. */
export function rateLabel(note: RateNote): string {
  if (note.source === "manual") return "converted by you";
  return `${note.source} rate, ${day(note.rateDate)}`;
}

/** The amount in the account's currency at `rate`, to the cent, or null when unknown. */
export function converted(amount: string | null | undefined, rate: string): string | null {
  const value = Number(amount);
  if (amount === null || amount === undefined || amount === "" || Number.isNaN(value)) return null;
  return (Math.round(value * Number(rate) * 100) / 100).toFixed(2);
}

/** "1197.00 UAH ≈ 103.42 PLN · NBP rate, 2 October". */
export function conversionLine(
  amount: string,
  currency: string,
  convertedAmount: string,
  accountCurrency: string,
  note: RateNote,
): string {
  return `${Number(amount).toFixed(2)} ${currency} ≈ ${convertedAmount} ${accountCurrency} · ${rateLabel(note)}`;
}

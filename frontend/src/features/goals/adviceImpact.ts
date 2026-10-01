import type { Recommendation } from "@/stores/AdviceStore";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const COUNT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

/**
 * What following a piece of advice is worth, as the server worked it out from the
 * receipts (BRD F4 — F8.5): "−20.47 PLN a month · 3 fewer purchases a month".
 */
export function impactOf(advice: Recommendation, currency: string): string {
  const saving = `−${AMOUNT.format(Number(advice.monthly_saving))} ${currency} a month`;
  const avoided = Number(advice.purchases_avoided);
  if (advice.purchases_avoided === null || avoided === 0) return saving;
  const noun = avoided === 1 ? "purchase" : "purchases";
  return `${saving} · ${COUNT.format(avoided)} fewer ${noun}`;
}

import i18n from "@/i18n";
import type { Recommendation } from "@/stores/AdviceStore";
import { numberFormat } from "@/i18n/format";

const AMOUNT = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const COUNT = numberFormat({ maximumFractionDigits: 1 });

/**
 * What following a piece of advice is worth, as the server worked it out from the
 * receipts (BRD F4 — F8.5): "−20.47 PLN a month · 3 fewer purchases a month".
 */
export function impactOf(advice: Recommendation, currency: string): string {
  const saving = i18n.t("goals:impact.saving", {
    amount: AMOUNT.format(Number(advice.monthly_saving)),
    currency,
  });
  const avoided = Number(advice.purchases_avoided);
  if (advice.purchases_avoided === null || avoided === 0) return saving;
  const fewer = i18n.t("goals:impact.avoided", {
    count: avoided,
    formatted: COUNT.format(avoided),
  });
  return `${saving} · ${fewer}`;
}

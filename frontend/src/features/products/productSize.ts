import i18n from "@/i18n";
import { numberFormat } from "@/i18n/format";

const AMOUNT = numberFormat({ maximumFractionDigits: 3 });

/** A package size as a shopper writes it: "330 ml", "1,5 l", "600 g" (F16.1). */
export function productSize(amount: string | null, unit: string | null): string | null {
  if (amount === null || (unit !== "g" && unit !== "ml")) return null;
  const value = Number(amount);
  const large = value >= 1000;
  const shown = AMOUNT.format(large ? value / 1000 : value);
  const key = unit === "g" ? (large ? "kg" : "g") : large ? "l" : "ml";
  return `${shown} ${i18n.t(`products:units.${key}`)}`;
}

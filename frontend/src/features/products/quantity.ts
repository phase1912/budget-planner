import i18n from "@/i18n";
import { numberFormat } from "@/i18n/format";

const AMOUNT = numberFormat({ maximumFractionDigits: 2 });

/**
 * A bought quantity as a shopper says it (F16.2): "1,25 kg", "750 ml", "3 pcs". Grams and
 * millilitres turn into kilograms and litres from a thousand up.
 */
export function quantityLabel(unit: string, amount: string | number): string {
  const value = Number(amount);
  if (unit === "g" || unit === "ml") {
    const large = value >= 1000;
    const key = unit === "g" ? (large ? "kg" : "g") : large ? "l" : "ml";
    return `${AMOUNT.format(large ? value / 1000 : value)} ${i18n.t(`products:units.${key}`)}`;
  }
  return i18n.t("products:units.pieces", { count: value, amount: AMOUNT.format(value) });
}

/** The unit a price per kilogram or litre is for, or a piece where no size is known. */
export function priceUnit(sizeUnit: string | null): string {
  if (sizeUnit === "g") return i18n.t("products:units.kg");
  if (sizeUnit === "ml") return i18n.t("products:units.l");
  return i18n.t("products:units.piece");
}

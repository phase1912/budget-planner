import { TrendingDown } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatAmount, numberFormat } from "@/i18n/format";
import type { Product } from "@/stores/ProductsStore";
import { priceUnit } from "../quantity";

const PERCENT = numberFormat({ maximumFractionDigits: 0 });

/**
 * "Cheaper at Lidl: 0.50 PLN/pc less (10%)" — where a product recently cost less than at
 * the shop it was last bought in (F16.3), for one item. Renders nothing when there is no
 * such shop.
 */
export function CheaperMark({
  product,
  currency,
}: {
  product: Product | undefined;
  currency: string;
}) {
  const { t } = useTranslation("products");
  const cheaper = product?.cheaper;
  if (!product || !cheaper) return null;
  return (
    <span className="inline-flex items-start gap-1.5 text-base font-semibold text-tone-primary-text">
      <TrendingDown size={14} aria-hidden="true" className="mt-0.5 shrink-0" />
      <span>
        {t("cheaper.mark", {
          shop: cheaper.shop,
          amount: formatAmount(cheaper.difference),
          currency,
          unit: priceUnit(null),
          percent: cheaper.percent ? PERCENT.format(Number(cheaper.percent)) : "—",
          instead: cheaper.instead_of,
        })}
      </span>
    </span>
  );
}

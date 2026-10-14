import { useTranslation } from "react-i18next";

import { Pill } from "@/shared/components";
import { dateFormat, formatAmount, numberFormat } from "@/i18n/format";
import type { Exploration } from "@/stores/ExplorationStore";
import { priceUnit } from "../quantity";

type ProductPurchases = Exploration["products"][number];

const DAY = dateFormat({ day: "numeric", month: "short" });
const PERCENT = numberFormat({ maximumFractionDigits: 1 });

/**
 * What one product cost in each shop (F16.2.2): the latest and average price per unit —
 * per kg or l where its size is known — cheapest first, and how much more each other shop
 * charged. A row per shop on a phone and tablet, a table's columns on a wide screen.
 */
export function ShopPrices({ product, currency }: { product: ProductPurchases; currency: string }) {
  const { t } = useTranslation("products");
  const unit = priceUnit(product.product.size_unit);
  return (
    <div className="flex flex-col gap-1.5">
      <div
        aria-hidden="true"
        className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_8rem_8rem_10rem] gap-x-3 px-3 text-sm font-semibold uppercase tracking-[0.05em] text-muted-foreground"
      >
        <span>{t("explore.shop")}</span>
        <span className="text-right">{t("explore.latest", { unit })}</span>
        <span className="text-right">{t("explore.average", { unit })}</span>
        <span className="text-right">{t("explore.difference")}</span>
      </div>
      <ul
        aria-label={t("explore.shopsOf", { name: product.product.name })}
        className="m-0 flex list-none flex-col divide-y divide-border rounded-control border border-border p-0"
      >
        {product.shops.map((shop, index) => (
          <li
            key={shop.shop}
            className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 px-3 py-2.5 lg:grid-cols-[minmax(0,1fr)_8rem_8rem_10rem] lg:items-center"
          >
            <span className="flex min-w-0 flex-col">
              <span className="break-words text-md font-semibold">{shop.shop}</span>
              <span className="text-base text-muted-foreground">
                {t("explore.lastBought", {
                  count: shop.purchases,
                  date: DAY.format(new Date(`${shop.latest_day}T00:00:00`)),
                })}
              </span>
            </span>
            <span className="text-right tabular-nums text-md font-semibold">
              {formatAmount(shop.latest)} {currency}
              <span className="font-normal text-muted-foreground lg:hidden"> / {unit}</span>
            </span>
            <span className="col-span-2 text-base tabular-nums text-muted-foreground lg:col-span-1 lg:text-right lg:text-md">
              <span className="lg:hidden">{t("explore.averageShort")} </span>
              {formatAmount(shop.average)} {currency}
            </span>
            <span className="col-span-2 lg:col-span-1 lg:text-right">
              {index === 0 ? (
                <Pill tone="success" size="sm">
                  {t("explore.cheapest")}
                </Pill>
              ) : (
                <span className="tabular-nums text-md font-semibold text-tone-warning-text">
                  {t("explore.more", {
                    amount: `${formatAmount(shop.above_cheapest)} ${currency}`,
                    percent: shop.above_percent ? PERCENT.format(Number(shop.above_percent)) : "—",
                  })}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

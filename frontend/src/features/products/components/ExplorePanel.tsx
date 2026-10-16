import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import {
  Card,
  DateRangeFilter,
  ErrorState,
  LoadingState,
  SegmentedControl,
} from "@/shared/components";
import { formatAmount, numberFormat } from "@/i18n/format";
import type { ExplorePreset } from "@/stores/ExplorationStore";
import { useStores } from "@/stores/StoreContext";
import { periodLabel } from "@/features/statistics/periodLabel";
import { priceUnit, quantityLabel } from "../quantity";
import { CheaperMark } from "./CheaperMark";
import { MonthBars } from "./MonthBars";
import { PriceChart } from "./PriceChart";
import { ShopPrices } from "./ShopPrices";

const PERCENT = numberFormat({ maximumFractionDigits: 1, signDisplay: "always" });

/**
 * What the ticked products were bought for over a period (F16.2): how often, how much and
 * what it cost, month by month; for each product, its price in each shop; and for one
 * product, how its price moved. Shown above the products list while anything is ticked.
 */
export const ExplorePanel = observer(function ExplorePanel({ currency }: { currency: string }) {
  const { explorationStore, productsStore } = useStores();
  const listed = (id: string) => productsStore.productById(id);
  const { t } = useTranslation(["products", "statistics"]);
  const [picking, setPicking] = useState(false);
  const { result, isLoading, error, preset, start, end } = explorationStore;

  return (
    <Card variant="surface" className="flex flex-col gap-5 px-3.5 py-4 md:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <SegmentedControl<ExplorePreset>
          label={t("statistics:period")}
          size="sm"
          fill
          value={preset}
          onChange={(chosen) => {
            if (chosen === "custom") setPicking(true);
            else explorationStore.choosePreset(chosen);
          }}
          options={[
            {
              value: "this_month",
              label: t("statistics:presets.thisMonth"),
              shortLabel: t("statistics:presets.thisMonthShort"),
            },
            {
              value: "last_month",
              label: t("statistics:presets.lastMonth"),
              shortLabel: t("statistics:presets.lastMonthShort"),
            },
            {
              value: "last_3_months",
              label: t("statistics:presets.last3"),
              shortLabel: t("statistics:presets.last3Short"),
            },
            { value: "all", label: t("explore.allTime"), shortLabel: t("explore.allTimeShort") },
            { value: "custom", label: t("statistics:presets.custom") },
          ]}
        />
        <DateRangeFilter
          start={start ?? undefined}
          end={end ?? undefined}
          label={start && end ? periodLabel(start, end) : t("explore.allTime")}
          allowAll={false}
          isOpen={picking}
          onOpenChange={setPicking}
          onApply={(from, to) => {
            if (from && to) explorationStore.chooseRange(from, to);
          }}
        />
      </div>

      {error ? (
        <ErrorState layout="banner" title={t("explore.failed")} message={error} />
      ) : !result ? (
        isLoading && <LoadingState title={t("explore.loading")} />
      ) : result.totals.times === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("explore.nothing")}</p>
      ) : (
        <>
          <dl className="m-0 grid grid-cols-2 gap-3 md:grid-cols-3">
            <div className="flex flex-col gap-0.5">
              <dt className="text-base text-muted-foreground">{t("explore.bought")}</dt>
              <dd className="m-0 text-lg font-semibold tabular-nums">
                {t("explore.times", { count: result.totals.times })}
              </dd>
            </div>
            <div className="flex flex-col gap-0.5">
              <dt className="text-base text-muted-foreground">{t("explore.spent")}</dt>
              <dd className="m-0 text-lg font-semibold tabular-nums">
                {formatAmount(result.totals.spent)} {currency}
              </dd>
            </div>
            <div className="col-span-2 flex flex-col gap-0.5 md:col-span-1">
              <dt className="text-base text-muted-foreground">{t("explore.quantity")}</dt>
              <dd className="m-0 text-lg font-semibold tabular-nums">
                {Object.entries(result.totals.quantities)
                  .map(([unit, amount]) => quantityLabel(unit, amount))
                  .join(" · ")}
              </dd>
            </div>
          </dl>

          {result.months.length > 1 && <MonthBars months={result.months} currency={currency} />}

          {result.products.map((product) => (
            <section
              key={product.product.id}
              className="flex flex-col gap-3 border-t border-border pt-4"
            >
              <h3 className="m-0 break-words text-lg font-semibold">
                {product.product.name}
                <span className="ml-2 text-md font-normal text-muted-foreground">
                  {t("explore.times", { count: product.amounts.times })} ·{" "}
                  {formatAmount(product.amounts.spent)} {currency}
                </span>
              </h3>
              <CheaperMark product={listed(product.product.id)} currency={currency} />
              {product.change && (
                <p className="m-0 text-md">
                  {t("explore.change", {
                    unit: priceUnit(product.product.size_unit),
                    from: formatAmount(product.change.first),
                    to: formatAmount(product.change.last),
                    currency,
                    percent: product.change.percent
                      ? PERCENT.format(Number(product.change.percent))
                      : "—",
                  })}
                </p>
              )}
              {product.shops.length > 1 && <ShopPrices product={product} currency={currency} />}
              {result.products.length === 1 && product.prices.length > 1 && (
                <PriceChart product={product} currency={currency} />
              )}
              {/* One price is no trend: say why there is no chart rather than showing nothing. */}
              {result.products.length === 1 && product.prices.length === 1 && (
                <p className="m-0 text-base text-muted-foreground">{t("explore.oneTime")}</p>
              )}
            </section>
          ))}
        </>
      )}
    </Card>
  );
});

import { useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Button,
  Card,
  DateRangeFilter,
  ErrorState,
  LoadingState,
  Pill,
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

const PERCENT = numberFormat({ maximumFractionDigits: 0, signDisplay: "always" });
const PRECISE = numberFormat({ maximumFractionDigits: 1, signDisplay: "always" });

interface ExplorePanelProps {
  currency: string;
  /** The saved selection the ticked products are, if they are one. */
  selectionName: string | null;
  onSave: () => void;
  onMerge: () => void;
}

/**
 * What the ticked products were bought for over a period (F16.2, explore.html): the
 * products as chips to drop or add to, how often, how much and what a month, month by
 * month; for each product its change and price in each shop; and for one product, how
 * its price moved. Saving the products as a selection and merging them start here.
 */
export const ExplorePanel = observer(function ExplorePanel({
  currency,
  selectionName,
  onSave,
  onMerge,
}: ExplorePanelProps) {
  const { explorationStore, productsStore } = useStores();
  const listed = (id: string) => productsStore.productById(id);
  const { t } = useTranslation(["products", "statistics"]);
  const [picking, setPicking] = useState(false);
  const { result, isLoading, error, preset, start, end } = explorationStore;
  const months = result?.months.length ?? 0;
  const tile = "flex flex-col gap-0.5 rounded-control control-fill p-3";

  return (
    <Card className="flex flex-col gap-4 px-3.5 py-4 md:px-5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <h2 className="m-0 min-w-0 break-words text-2xl font-extrabold">
          {selectionName ?? t("explore.title")}
        </h2>
        <span className="flex shrink-0 gap-2">
          {productsStore.selected.length > 1 && (
            <Button variant="secondary" size="sm" className="min-h-11" onClick={onMerge}>
              {t("merge.open")}
            </Button>
          )}
          {!selectionName && (
            <Button variant="secondary" size="sm" className="min-h-11" onClick={onSave}>
              {t("explore.save")}
            </Button>
          )}
        </span>
      </div>

      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {productsStore.selectedProducts.map((product) => (
          <li key={product.id}>
            <span className="flex min-h-10 items-center gap-1 rounded-pill bg-primary pr-1 pl-3.5 text-md font-bold text-primary-foreground">
              <span className="max-w-48 truncate">{product.name}</span>
              <button
                type="button"
                aria-label={t("explore.remove", { name: product.name })}
                className="flex h-9 w-9 items-center justify-center rounded-pill"
                onClick={() => {
                  productsStore.toggle(product.id);
                }}
              >
                <X size={14} aria-hidden="true" />
              </button>
            </span>
          </li>
        ))}
        <li>
          <a
            href="#all-products"
            className="control-fill flex min-h-10 items-center gap-1 rounded-pill px-3.5 text-md font-bold text-foreground"
          >
            <Plus size={14} aria-hidden="true" />
            {t("explore.add")}
          </a>
        </li>
        <li className="flex">
          <button
            type="button"
            className="min-h-10 px-2 text-md font-bold text-muted-foreground"
            onClick={() => {
              productsStore.clearSelection();
            }}
          >
            {t("clear")}
          </button>
        </li>
      </ul>

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
              value: "last_3_months",
              label: t("statistics:presets.last3"),
              shortLabel: t("statistics:presets.last3Short"),
            },
            { value: "all", label: t("explore.allTime"), shortLabel: t("explore.allTimeShort") },
            { value: "custom", label: t("statistics:presets.custom") },
          ]}
        />
        {/* The quick periods name themselves; the dates matter only for one's own. */}
        {(preset === "custom" || picking) && (
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
        )}
      </div>

      {error ? (
        <ErrorState layout="banner" title={t("explore.failed")} message={error} />
      ) : !result ? (
        isLoading && <LoadingState title={t("explore.loading")} />
      ) : result.totals.times === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("explore.nothing")}</p>
      ) : (
        <>
          <dl className="m-0 grid grid-cols-3 gap-2">
            <div className={tile}>
              <dt className="text-sm text-muted-foreground">{t("explore.bought")}</dt>
              <dd className="m-0 text-xl font-extrabold tabular-nums">{result.totals.times}×</dd>
            </div>
            <div className={tile}>
              <dt className="text-sm text-muted-foreground">{t("explore.spent")}</dt>
              <dd className="m-0 text-xl font-extrabold tabular-nums">
                {formatAmount(result.totals.spent)}
              </dd>
            </div>
            <div className={tile}>
              <dt className="text-sm text-muted-foreground">{t("explore.perMonth")}</dt>
              <dd className="m-0 text-xl font-extrabold tabular-nums">
                {formatAmount(String(Number(result.totals.spent) / Math.max(1, months)))}
              </dd>
            </div>
          </dl>

          {months > 1 && <MonthBars months={result.months} currency={currency} />}

          <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
            {result.products.map((product) => {
              const mostly = [...product.shops].sort((a, b) => b.purchases - a.purchases)[0];
              const percent = product.change?.percent;
              return (
                <li key={product.product.id} className="flex flex-col gap-3 py-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <span className="flex min-w-0 flex-col gap-0.5">
                      <span className="break-words text-lg font-bold">{product.product.name}</span>
                      <span className="text-md text-muted-foreground tabular-nums">
                        {[
                          `${String(product.amounts.times)}×`,
                          ...Object.entries(product.amounts.quantities).map(([unit, amount]) =>
                            quantityLabel(unit, amount),
                          ),
                          mostly && t("explore.mostly", { shop: mostly.shop }),
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </span>
                    <span className="flex shrink-0 flex-col items-end gap-1">
                      <span className="text-lg font-extrabold tabular-nums">
                        {formatAmount(product.amounts.spent)} {currency}
                      </span>
                      {percent && Number(percent) !== 0 && (
                        <Pill tone={Number(percent) > 0 ? "error" : "success"} size="sm">
                          {t("explore.changePill", {
                            percent: PERCENT.format(Number(percent)),
                            unit: priceUnit(product.product.size_unit),
                          })}
                        </Pill>
                      )}
                    </span>
                  </div>
                  <CheaperMark product={listed(product.product.id)} currency={currency} />
                  {product.change && result.products.length === 1 && (
                    <p className="m-0 text-md">
                      {t("explore.change", {
                        unit: priceUnit(product.product.size_unit),
                        from: formatAmount(product.change.first),
                        to: formatAmount(product.change.last),
                        currency,
                        percent: product.change.percent
                          ? PRECISE.format(Number(product.change.percent))
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
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Card>
  );
});

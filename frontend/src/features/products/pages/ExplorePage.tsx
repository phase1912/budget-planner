import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { reaction } from "mobx";
import { Pencil, Plus, RotateCcw, Search, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  BackLink,
  DateRangeFilter,
  ErrorState,
  Input,
  LoadingState,
  SegmentedControl,
} from "@/shared/components";
import { formatAmount, numberFormat } from "@/i18n/format";
import type { ExplorePreset } from "@/stores/ExplorationStore";
import { useStores } from "@/stores/StoreContext";
import { periodLabel } from "@/features/statistics/periodLabel";
import { SettingsSheet } from "@/features/profile/components/SettingsRows";
import { priceUnit, quantityLabel } from "../quantity";
import { CheaperMark } from "../components/CheaperMark";
import { MonthBars } from "../components/MonthBars";
import { PriceChart } from "../components/PriceChart";
import { ShopPrices } from "../components/ShopPrices";
import { SaveSelectionDialog } from "../components/SaveSelectionDialog";
import { MergeProductsDialog } from "../components/MergeProductsDialog";
import { RenameProductDialog } from "../components/RenameProductDialog";
import { productColour } from "../productColours";

const PERCENT = numberFormat({ maximumFractionDigits: 0 });
const PRECISE = numberFormat({ maximumFractionDigits: 1, signDisplay: "always" });

/**
 * Exploring several products together (F16.2, explore.html): the saved sets, the products
 * as coloured chips, a period, three figures, the months as columns stacked by product
 * and a row per product — each opening to its prices by shop and over time. Saving the
 * products as a set and merging them start here.
 */
export const ExplorePage = observer(function ExplorePage() {
  const { explorationStore, productsStore, authStore } = useStores();
  const { t } = useTranslation(["products", "statistics", "common"]);
  const [picking, setPicking] = useState(false);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [merging, setMerging] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null);
  const { result, isLoading, error, preset, start, end } = explorationStore;
  const selected = productsStore.selected;
  const openSet = explorationStore.selectionMatching(selected);
  const months = result?.months.length ?? 0;
  const currency = authStore.user?.currency ?? "PLN";

  // Reached from far down the products list: the screen opens at its top.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    if (productsStore.products.length === 0) void productsStore.load();
    void explorationStore.loadSelections();
  }, [productsStore, explorationStore]);

  // What is ticked is what is explored, whichever way it was ticked.
  useEffect(
    () =>
      reaction(
        () => productsStore.selected.slice(),
        (ids) => {
          explorationStore.setProducts(ids);
        },
        { fireImmediately: true },
      ),
    [productsStore, explorationStore],
  );

  const colourOf = (id: string) => productColour(selected.indexOf(id));
  const tile = "flex flex-col gap-0.5 rounded-card bg-surface p-3.5";
  const saveLabel = explorationStore.changedSet ? t("explore.saveChanges") : t("explore.save");

  return (
    <div className="flex-grow flex flex-col items-center pb-4">
      <div className="w-full max-w-[1000px] flex flex-col gap-4">
        <header className="flex items-center gap-3">
          <BackLink to="/products" label={t("common:nav.products")} />
          <h1 className="m-0 min-w-0 flex-1 truncate text-3xl font-extrabold tracking-[-0.02em]">
            {openSet?.name ?? t("explore.title")}
          </h1>
          {selected.length > 0 && !openSet && (
            <button
              type="button"
              className="min-h-11 shrink-0 rounded-control bg-tone-primary-bg px-4 text-lg font-extrabold text-primary"
              aria-label={saveLabel}
              onClick={() => {
                setSaving(true);
              }}
            >
              <span className="md:hidden">{t("explore.saveShort")}</span>
              <span className="hidden md:inline">{saveLabel}</span>
            </button>
          )}
        </header>

        {(explorationStore.selections.length > 0 || selected.length > 0) && (
          <ul aria-label={t("selections.title")} className="m-0 flex list-none flex-wrap gap-2 p-0">
            {explorationStore.selections.map((set) => (
              <li key={set.id}>
                <button
                  type="button"
                  aria-pressed={openSet?.id === set.id}
                  onClick={() => {
                    productsStore.select(set.product_ids);
                    explorationStore.openSet(set.id);
                  }}
                  className={`min-h-11 rounded-pill border-2 px-4 text-md font-bold ${
                    openSet?.id === set.id
                      ? "border-primary bg-tone-primary-bg text-primary"
                      : "border-border-strong text-foreground"
                  }`}
                >
                  {set.name}
                </button>
              </li>
            ))}
            {selected.length > 0 && (
              <li>
                <button
                  type="button"
                  onClick={() => {
                    productsStore.clearSelection();
                    explorationStore.openSet(null);
                  }}
                  className="flex min-h-11 items-center gap-1.5 rounded-pill px-3.5 text-md font-bold text-muted-foreground"
                >
                  <RotateCcw size={14} aria-hidden="true" />
                  {t("selections.clear")}
                </button>
              </li>
            )}
          </ul>
        )}

        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {productsStore.selectedProducts.map((product) => (
            <li key={product.id}>
              <span
                className="flex min-h-11 items-center gap-2 rounded-pill pr-1 pl-3.5 text-md font-bold"
                style={{
                  background: `color-mix(in srgb, ${colourOf(product.id)} 22%, transparent)`,
                }}
              >
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-pill"
                  style={{ background: colourOf(product.id) }}
                  aria-hidden="true"
                />
                <span className="max-w-44 truncate">{product.name}</span>
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
            <button
              type="button"
              className="flex min-h-11 items-center gap-1 rounded-pill border-2 border-dashed border-border-strong px-3.5 text-md font-bold text-muted-foreground"
              onClick={() => {
                setAdding(true);
              }}
            >
              <Plus size={14} aria-hidden="true" />
              {t("explore.add")}
            </button>
          </li>
        </ul>

        {selected.length === 0 ? (
          <p className="m-0 rounded-card bg-surface p-4 text-md text-muted-foreground">
            {t("explore.pickFirst")}
          </p>
        ) : (
          <>
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
                { value: "this_month", label: t("explore.month") },
                { value: "last_3_months", label: t("explore.months3") },
                { value: "last_6_months", label: t("explore.months6") },
                { value: "all", label: t("explore.allTimeShort") },
                { value: "custom", label: t("statistics:presets.custom") },
              ]}
            />
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

            {error ? (
              <ErrorState layout="banner" title={t("explore.failed")} message={error} />
            ) : !result ? (
              isLoading && <LoadingState title={t("explore.loading")} />
            ) : result.totals.times === 0 ? (
              <p className="m-0 rounded-card bg-surface p-4 text-md text-muted-foreground">
                {t("explore.nothing")}
              </p>
            ) : (
              <>
                <dl className="m-0 grid grid-cols-3 gap-2.5">
                  <div className={tile}>
                    <dt className="text-md text-muted-foreground">{t("explore.bought")}</dt>
                    <dd className="m-0 text-2xl font-extrabold tabular-nums">
                      {result.totals.times}×
                    </dd>
                  </div>
                  <div className={tile}>
                    <dt className="text-md text-muted-foreground">{t("explore.spent")}</dt>
                    <dd className="m-0 text-2xl font-extrabold tabular-nums">
                      {formatAmount(result.totals.spent)}
                    </dd>
                  </div>
                  <div className={tile}>
                    <dt className="text-md text-muted-foreground">{t("explore.perMonth")}</dt>
                    <dd className="m-0 text-2xl font-extrabold tabular-nums">
                      {formatAmount(String(Number(result.totals.spent) / Math.max(1, months)))}
                    </dd>
                  </div>
                </dl>

                {months > 1 && (
                  <MonthBars months={result.months} currency={currency} colourOf={colourOf} />
                )}

                <ul className="m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-card bg-surface p-0">
                  {result.products.map((product) => {
                    const id = product.product.id;
                    const mostly = [...product.shops].sort((a, b) => b.purchases - a.purchases)[0];
                    const percent = product.change?.percent;
                    const isOpen = open === id || result.products.length === 1;
                    return (
                      <li key={id} className="on-surface">
                        <button
                          type="button"
                          aria-expanded={isOpen}
                          onClick={() => {
                            setOpen(open === id ? null : id);
                          }}
                          className="flex w-full items-center gap-3.5 px-4 py-3.5 text-left"
                        >
                          <span
                            className="w-1.5 self-stretch rounded-pill"
                            style={{ background: colourOf(id) }}
                            aria-hidden="true"
                          />
                          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                            <span className="break-words text-lg font-extrabold">
                              {product.product.name}
                            </span>
                            <span className="text-md text-muted-foreground tabular-nums">
                              {[
                                `${String(product.amounts.times)}×`,
                                ...Object.entries(product.amounts.quantities).map(
                                  ([unit, amount]) => quantityLabel(unit, amount),
                                ),
                                mostly && t("explore.mostly", { shop: mostly.shop }),
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </span>
                          </span>
                          <span className="flex shrink-0 flex-col items-end gap-0.5">
                            <span className="text-lg font-extrabold tabular-nums">
                              {formatAmount(product.amounts.spent)} {currency}
                            </span>
                            {percent && Number(percent) !== 0 && (
                              <span
                                className={`text-md font-bold tabular-nums ${
                                  Number(percent) > 0 ? "text-error" : "text-success"
                                }`}
                              >
                                {Number(percent) > 0 ? "▲" : "▼"}{" "}
                                {t("explore.changeUnit", {
                                  percent: PERCENT.format(Math.abs(Number(percent))),
                                  unit: priceUnit(product.product.size_unit),
                                })}
                              </span>
                            )}
                          </span>
                        </button>
                        {isOpen && (
                          <div className="flex flex-col gap-3 px-4 pb-4">
                            <button
                              type="button"
                              className="flex min-h-11 items-center gap-1.5 self-start text-md font-bold text-primary"
                              onClick={() => {
                                setRenaming({ id, name: product.product.name });
                              }}
                            >
                              <Pencil size={14} aria-hidden="true" />
                              {t("rename.open")}
                            </button>
                            <CheaperMark product={listedProduct(id)} currency={currency} />
                            {product.change && (
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
                            {product.shops.length > 1 && (
                              <ShopPrices product={product} currency={currency} />
                            )}
                            {product.prices.length > 1 ? (
                              <PriceChart product={product} currency={currency} />
                            ) : (
                              <p className="m-0 text-base text-muted-foreground">
                                {t("explore.oneTime")}
                              </p>
                            )}
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
          </>
        )}
        {/* Two products that are one, printed differently, are merged from here too. */}
        {selected.length > 1 && (
          <button
            type="button"
            className="min-h-11 self-start text-md font-bold text-muted-foreground"
            onClick={() => {
              setMerging(true);
            }}
          >
            {t("merge.open")}
          </button>
        )}
      </div>

      {adding && (
        <AddProductsSheet
          onClose={() => {
            setAdding(false);
          }}
        />
      )}
      {saving && (
        <SaveSelectionDialog
          onClose={() => {
            setSaving(false);
          }}
        />
      )}
      {renaming && (
        <RenameProductDialog
          productId={renaming.id}
          current={renaming.name}
          onClose={() => {
            setRenaming(null);
          }}
          onRenamed={() => void explorationStore.load()}
        />
      )}
      {merging && (
        <MergeProductsDialog
          onClose={() => {
            setMerging(false);
          }}
        />
      )}
    </div>
  );

  function listedProduct(id: string) {
    return productsStore.productById(id);
  }
});

/** Picking more products to explore, by name, without leaving the screen. */
const AddProductsSheet = observer(function AddProductsSheet({ onClose }: { onClose: () => void }) {
  const { productsStore } = useStores();
  const { t } = useTranslation("products");
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const found = productsStore.products
    .filter((p) => !needle || p.name.toLowerCase().includes(needle))
    .slice(0, 40);
  return (
    <SettingsSheet title={t("explore.add")} onClose={onClose}>
      <div className="relative">
        <Search
          size={16}
          aria-hidden="true"
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          type="search"
          aria-label={t("search")}
          placeholder={t("search")}
          className="w-full pl-10"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
          }}
        />
      </div>
      <ul className="m-0 flex max-h-[50vh] list-none flex-col overflow-y-auto p-0">
        {found.map((product) => {
          const ticked = productsStore.selected.includes(product.id);
          return (
            <li key={product.id}>
              <label className="flex min-h-12 cursor-pointer items-center gap-3 py-1.5">
                <input
                  type="checkbox"
                  className="h-5 w-5 accent-[var(--color-primary)]"
                  checked={ticked}
                  onChange={() => {
                    productsStore.toggle(product.id);
                  }}
                />
                <span className="min-w-0 flex-1 truncate text-lg">{product.name}</span>
              </label>
            </li>
          );
        })}
      </ul>
    </SettingsSheet>
  );
});

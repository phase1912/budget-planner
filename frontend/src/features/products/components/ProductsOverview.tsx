import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Pill, SegmentedControl } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";

type View = "prices" | "most" | "shops";

const PRICE = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });
const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const PERCENT = numberFormat({ maximumFractionDigits: 0, signDisplay: "always" });
/** A colour per shop in "where it costs what", from the palette's chart series. */
const SHOP_COLOURS = [
  "bg-[var(--cat-groceries)]",
  "bg-[var(--cat-transport)]",
  "bg-[var(--cat-dining)]",
  "bg-[var(--cat-utilities)]",
  "bg-[var(--cat-health)]",
];

/**
 * Products at a glance (F23.5), over the last six months: whose price moved — tap one to
 * see where it costs what (products.html), and explore it month by month from there —
 * what is bought most, and in which shop the usual products are cheapest, with what was
 * paid above the cheapest price elsewhere.
 */
export const ProductsOverview = observer(function ProductsOverview({
  currency,
}: {
  currency: string;
}) {
  const { productsStore } = useStores();
  const { t } = useTranslation("products");
  const [view, setView] = useState<View>("prices");
  const [opened, setOpened] = useState<string | null>(null);
  const overview = productsStore.overview;
  const most = [...productsStore.products].sort((a, b) => b.purchases - a.purchases).slice(0, 8);
  const navigate = useNavigate();
  const explore = (id: string) => {
    productsStore.select([id]);
    void navigate("/products/explore");
  };
  const widestShop = Math.max(1, ...(overview?.shops.map((s) => s.cheapest_for) ?? [1]));

  return (
    <section aria-label={t("overview.label")} className="flex flex-col gap-3">
      <SegmentedControl<View>
        label={t("overview.label")}
        size="sm"
        fill
        value={view}
        onChange={setView}
        options={[
          { value: "prices", label: t("overview.prices"), shortLabel: t("overview.pricesShort") },
          { value: "most", label: t("overview.most"), shortLabel: t("overview.mostShort") },
          { value: "shops", label: t("overview.shops"), shortLabel: t("overview.shopsShort") },
        ]}
      />

      {view === "prices" &&
        (!overview || overview.moves.length === 0 ? (
          <p className="m-0 rounded-card bg-surface p-4 text-md text-muted-foreground">
            {t("overview.noMoves")}
          </p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {overview.moves.map((move) => {
              const up = Number(move.change.difference) > 0;
              const low = Math.min(...move.history.map(Number));
              const high = Math.max(...move.history.map(Number));
              const isOpen = opened === move.product.id;
              const dearest = Math.max(1, ...move.shops.map((shop) => Number(shop.latest)));
              return (
                <li
                  key={move.product.id}
                  className={`overflow-hidden rounded-card border-2 bg-surface ${
                    isOpen ? "border-primary" : "border-transparent"
                  }`}
                >
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => {
                      setOpened(isOpen ? null : move.product.id);
                    }}
                    className="flex w-full items-center gap-3 p-3.5 text-left"
                  >
                    <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="truncate text-lg font-bold">{move.product.name}</span>
                      <span className="text-base text-muted-foreground tabular-nums">
                        {t("overview.moveLine", {
                          shop: move.last_shop ?? "—",
                          first: PRICE.format(Number(move.change.first)),
                          last: PRICE.format(Number(move.change.last)),
                          currency,
                        })}
                      </span>
                    </span>
                    <span className="flex h-7 items-end gap-0.75" aria-hidden="true">
                      {move.history.map((price, i) => (
                        <span
                          key={i}
                          className={`w-1.25 rounded-sm ${
                            i === move.history.length - 1
                              ? up
                                ? "bg-error"
                                : "bg-success"
                              : "bg-border-strong"
                          }`}
                          style={{
                            height: `${String(30 + ((Number(price) - low) / (high - low || 1)) * 70)}%`,
                          }}
                        />
                      ))}
                    </span>
                    <Pill tone={up ? "error" : "success"} size="sm">
                      {PERCENT.format(Number(move.change.percent ?? 0))}%
                    </Pill>
                  </button>
                  {isOpen && (
                    <div className="flex flex-col gap-2.5 border-t border-border px-3.5 pt-3 pb-3.5">
                      {move.shops.length > 0 ? (
                        <>
                          <span className="text-sm font-bold tracking-[0.06em] text-muted-foreground uppercase">
                            {t("overview.where")}
                          </span>
                          <ul className="m-0 flex list-none flex-col gap-2 p-0">
                            {move.shops.map((shop, i) => (
                              <li
                                key={shop.shop}
                                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 md:grid-cols-[minmax(0,8rem)_minmax(0,1fr)_auto]"
                              >
                                <span className="truncate text-lg font-semibold">{shop.shop}</span>
                                <span className="text-lg font-bold tabular-nums md:order-last">
                                  {PRICE.format(Number(shop.latest))} {currency}
                                </span>
                                <span
                                  className="col-span-2 h-2 overflow-hidden rounded-pill bg-muted md:col-span-1"
                                  aria-hidden="true"
                                >
                                  <span
                                    className={`block h-2 rounded-pill ${SHOP_COLOURS[i % SHOP_COLOURS.length] ?? ""}`}
                                    style={{
                                      width: `${String((Number(shop.latest) / dearest) * 100)}%`,
                                    }}
                                  />
                                </span>
                              </li>
                            ))}
                          </ul>
                        </>
                      ) : (
                        <p className="m-0 text-md text-muted-foreground">{t("overview.oneShop")}</p>
                      )}
                      <button
                        type="button"
                        className="flex min-h-11 items-center justify-between gap-2 text-left text-lg font-bold text-primary"
                        onClick={() => {
                          explore(move.product.id);
                        }}
                      >
                        {t("overview.exploreOne")}
                        <ChevronRight size={18} aria-hidden="true" />
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        ))}

      {view === "most" && (
        <ul className="m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-card bg-surface p-0">
          {most.map((product) => (
            <li key={product.id}>
              <button
                type="button"
                onClick={() => {
                  explore(product.id);
                }}
                className="flex w-full items-center gap-3 px-3.5 py-3 text-left"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-md font-bold text-primary tabular-nums">
                  ×{product.purchases}
                </span>
                <span className="min-w-0 flex-1 truncate text-lg font-semibold">
                  {product.name}
                </span>
                <span className="text-lg font-bold tabular-nums">
                  {WHOLE.format(Number(product.spent))} {currency}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {view === "shops" &&
        (!overview || overview.shops.length === 0 ? (
          <p className="m-0 rounded-card bg-surface p-4 text-md text-muted-foreground">
            {t("overview.noShops")}
          </p>
        ) : (
          <div className="flex flex-col gap-2.5">
            {Number(overview.paid_above) > 0 && (
              <p className="m-0 rounded-card bg-primary p-4 text-lg font-bold text-primary-foreground">
                {t("overview.paidAbove", {
                  amount: WHOLE.format(Number(overview.paid_above)),
                  currency,
                })}
              </p>
            )}
            <p className="m-0 text-md text-muted-foreground">{t("overview.shopsHint")}</p>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {overview.shops.map((shop, i) => (
                <li key={shop.shop} className="flex flex-col gap-2 rounded-card bg-surface p-3.5">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="truncate text-lg font-bold">{shop.shop}</span>
                    <span className="text-base text-muted-foreground">
                      {t("overview.cheapestFor", { count: shop.cheapest_for })}
                    </span>
                  </span>
                  <span className="h-2.5 overflow-hidden rounded-pill bg-muted" aria-hidden="true">
                    <span
                      className={`block h-2.5 rounded-pill ${i === 0 ? "bg-success" : "bg-primary"}`}
                      style={{ width: `${String((shop.cheapest_for / widestShop) * 100)}%` }}
                    />
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
    </section>
  );
});

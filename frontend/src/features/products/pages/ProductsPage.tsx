import { useEffect, useState } from "react";
import { ChartLine, ChevronRight, Package, Search, X } from "lucide-react";
import { reaction } from "mobx";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Card, EmptyState, ErrorState, Input, LoadingState } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { ProductRow } from "../components/ProductRow";
import { ProductsOverview } from "../components/ProductsOverview";

/**
 * What the user buys, one product however each shop prints it (F16.1), and what it was
 * bought for (F16.2).
 *
 * Opening it matches every line not yet matched, so the first visit can take a moment.
 * Products are searched by any printed name. Ticked products are explored on their own
 * screen (ExplorePage) — a bar leads there — and saved sets open from here too. Each
 * product opens to the ways it was printed, any of which can be split off.
 */
export const ProductsPage = observer(function ProductsPage() {
  const { productsStore, authStore, explorationStore } = useStores();
  const { t } = useTranslation("products");
  const [draft, setDraft] = useState(productsStore.search);
  const currency = authStore.user?.currency ?? "PLN";
  const { products, isLoading, loadError, selected } = productsStore;
  // Ticks that are exactly a saved selection are already saved: no offer to save them again.
  const openSelection = explorationStore.selectionMatching(selected);

  useEffect(() => {
    void productsStore.load();
    void productsStore.loadOverview();
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

  useEffect(() => {
    if (draft === productsStore.search) return;
    const timer = setTimeout(() => {
      productsStore.setSearch(draft);
    }, 300);
    return () => {
      clearTimeout(timer);
    };
  }, [draft, productsStore]);

  return (
    <div className="flex-grow flex flex-col items-center pb-4">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <header className="flex flex-col gap-0.5">
          <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{t("title")}</h1>
          <p className="m-0 text-md text-muted-foreground">
            {t("count", { count: products.length })}
          </p>
        </header>

        <div className="relative">
          <Search
            size={16}
            aria-hidden="true"
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            type="search"
            className="min-h-12 rounded-control border-0 bg-surface pl-10 text-lg"
            aria-label={t("search")}
            placeholder={t("search")}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
            }}
          />
        </div>

        <Link
          to="/products/explore"
          className="flex min-h-15 items-center gap-3 rounded-card bg-primary px-4 py-3 text-primary-foreground"
        >
          <ChartLine size={22} aria-hidden="true" />
          <span className="flex flex-1 flex-col">
            <span className="text-lg font-extrabold">{t("exploreTitle")}</span>
            <span className="text-sm opacity-90">{t("exploreHint")}</span>
          </span>
          <ChevronRight size={18} aria-hidden="true" />
        </Link>

        <ProductsOverview currency={currency} />

        <h2 id="all-products" className="m-0 scroll-mt-4 pt-2 text-xl font-extrabold">
          {t("all")}
        </h2>

        {explorationStore.selections.length > 0 && (
          <section aria-label={t("selections.title")} className="flex flex-col gap-1.5">
            <h2 className="m-0 text-base font-medium text-muted-foreground">
              {t("selections.title")}
            </h2>
            <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
              {explorationStore.selections.map((selection) => (
                <li
                  key={selection.id}
                  className="inline-flex items-center rounded-pill control-fill"
                >
                  <button
                    type="button"
                    aria-pressed={openSelection?.id === selection.id}
                    className={`min-h-11 cursor-pointer rounded-l-pill px-3.5 text-md font-semibold md:min-h-0 md:py-1.5 ${
                      openSelection?.id === selection.id
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted"
                    }`}
                    onClick={() => {
                      productsStore.select(selection.product_ids);
                    }}
                  >
                    {selection.name}
                  </button>
                  <button
                    type="button"
                    aria-label={t("selections.delete", { name: selection.name })}
                    className="inline-flex min-h-11 w-10 cursor-pointer items-center justify-center rounded-r-pill text-muted-foreground hover:bg-muted hover:text-foreground md:min-h-0 md:w-8 md:py-1.5"
                    onClick={() => void explorationStore.deleteSelection(selection.id)}
                  >
                    <X size={14} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {loadError ? (
          <ErrorState layout="banner" title={t("loadFailed")} message={loadError} />
        ) : isLoading && products.length === 0 ? (
          <LoadingState title={t("loading")} />
        ) : products.length === 0 ? (
          <Card variant="surface" className="px-5 py-10">
            <EmptyState
              icon={Package}
              iconTone="primary"
              title={productsStore.search ? t("noMatch") : t("empty.title")}
              message={productsStore.search ? "" : t("empty.message")}
            />
          </Card>
        ) : (
          <Card flush>
            <ul
              aria-label={t("title")}
              className="m-0 flex list-none flex-col divide-y divide-border p-0"
            >
              {products.map((product) => (
                <ProductRow key={product.id} product={product} currency={currency} />
              ))}
            </ul>
          </Card>
        )}
      </div>
      {/* Ticked products are explored on their own screen; this is the way there. */}
      {selected.length > 0 && (
        <div className="pointer-events-none fixed inset-x-0 bottom-24 z-20 flex justify-center px-4 md:bottom-6">
          <Link
            to="/products/explore"
            className="pointer-events-auto flex min-h-13 items-center gap-3 rounded-pill bg-primary px-5 text-lg font-extrabold text-primary-foreground shadow-modal"
          >
            {openSelection ? openSelection.name : t("picked", { count: selected.length })}
            <span aria-hidden="true">·</span>
            {t("explore.go")}
            <ChevronRight size={18} aria-hidden="true" />
          </Link>
        </div>
      )}
    </div>
  );
});

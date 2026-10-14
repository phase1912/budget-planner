import { useEffect, useState } from "react";
import { Package, Search, X } from "lucide-react";
import { reaction } from "mobx";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { StatisticsTabs } from "@/features/statistics/components/StatisticsTabs";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Note,
} from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import { ExplorePanel } from "../components/ExplorePanel";
import { MergeProductsDialog } from "../components/MergeProductsDialog";
import { SaveSelectionDialog } from "../components/SaveSelectionDialog";
import { ProductRow } from "../components/ProductRow";

/**
 * What the user buys, one product however each shop prints it (F16.1), and what it was
 * bought for (F16.2).
 *
 * Opening it matches every line not yet matched, so the first visit can take a moment.
 * Products are searched by any printed name. Ticking products explores them over a period
 * — amounts, months, prices per shop — and the ticked set can be saved under a name and
 * opened again; ticking two or more also offers to merge them. Each product opens to the
 * ways it was printed, any of which can be split off.
 */
export const ProductsPage = observer(function ProductsPage() {
  const { productsStore, authStore, explorationStore } = useStores();
  const { t } = useTranslation("products");
  const [merging, setMerging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState(productsStore.search);
  const currency = authStore.user?.currency ?? "PLN";
  const { products, isLoading, loadError, selected } = productsStore;

  useEffect(() => {
    void productsStore.load();
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
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5">
        <header className="flex flex-col gap-1">
          <h1 className="m-0 text-[24px] font-bold tracking-[-0.02em] md:text-[28px]">
            {t("title")}
          </h1>
          <p className="m-0 text-lg text-muted-foreground">{t("subtitle")}</p>
        </header>

        <StatisticsTabs />

        {explorationStore.selections.length > 0 && (
          <section aria-label={t("selections.title")} className="flex flex-col gap-1.5">
            <h2 className="m-0 text-base font-medium text-muted-foreground">
              {t("selections.title")}
            </h2>
            <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
              {explorationStore.selections.map((selection) => (
                <li
                  key={selection.id}
                  className="inline-flex items-center rounded-pill border border-border bg-background"
                >
                  <button
                    type="button"
                    className="min-h-11 cursor-pointer rounded-l-pill px-3.5 text-md font-semibold hover:bg-muted md:min-h-0 md:py-1.5"
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

        <div className="relative">
          <Search
            size={16}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            type="search"
            className="pl-9"
            aria-label={t("search")}
            placeholder={t("search")}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
            }}
          />
        </div>

        {selected.length > 0 && (
          // Stays in view while ticking further down a long list, where the action is needed.
          <div className="sticky top-2 z-20 rounded-control bg-background shadow-raised">
            <Note tone="info">
              <span className="flex flex-col gap-2.5 md:flex-row md:items-center md:justify-between">
                <span>{t("picked", { count: selected.length })}</span>
                <span className="flex flex-wrap gap-2 [&>*]:flex-1 md:flex-nowrap md:[&>*]:flex-none">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      productsStore.clearSelection();
                    }}
                  >
                    {t("clear")}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setSaving(true);
                    }}
                  >
                    {t("selections.open")}
                  </Button>
                  {selected.length > 1 && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        setMerging(true);
                      }}
                    >
                      {t("merge.open")}
                    </Button>
                  )}
                </span>
              </span>
            </Note>
          </div>
        )}

        {selected.length > 0 && <ExplorePanel currency={currency} />}

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
      {saving && (
        <SaveSelectionDialog
          onClose={() => {
            setSaving(false);
          }}
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
});

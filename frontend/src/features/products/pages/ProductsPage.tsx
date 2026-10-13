import { useEffect, useState } from "react";
import { Package, Search } from "lucide-react";
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
import { MergeProductsDialog } from "../components/MergeProductsDialog";
import { ProductRow } from "../components/ProductRow";

/**
 * What the user buys, one product however each shop prints it (F16.1).
 *
 * Opening it matches every line not yet matched, so the first visit can take a moment.
 * Products are searched by any printed name; ticking two or more offers to merge them,
 * and each product opens to the ways it was printed, any of which can be split off.
 */
export const ProductsPage = observer(function ProductsPage() {
  const { productsStore, authStore } = useStores();
  const { t } = useTranslation("products");
  const [merging, setMerging] = useState(false);
  const [draft, setDraft] = useState(productsStore.search);
  const currency = authStore.user?.currency ?? "PLN";
  const { products, isLoading, loadError, selected } = productsStore;

  useEffect(() => {
    void productsStore.load();
  }, [productsStore]);

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
                <span>
                  {selected.length === 1
                    ? t("pickAnother")
                    : t("picked", { count: selected.length })}
                </span>
                <span className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none">
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
                    variant="primary"
                    size="sm"
                    disabled={selected.length < 2}
                    onClick={() => {
                      setMerging(true);
                    }}
                  >
                    {t("merge.open")}
                  </Button>
                </span>
              </span>
            </Note>
          </div>
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

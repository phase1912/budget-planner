import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";
import { CheckCircle2, Search, SlidersHorizontal } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import {
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  SegmentedControl,
} from "@/shared/components";
import type { ItemView, ReviewQueueItem } from "@/stores/CategoriesStore";
import { InlineCategoryPicker } from "../components/InlineCategoryPicker";

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

const EMPTY_MESSAGES: Record<ItemView, { title: string; message: string }> = {
  needs_review: {
    title: "Nothing needs review",
    message: "Every item the agent has seen was placed with confidence.",
  },
  corrected: {
    title: "No corrections yet",
    message: "Items you file under a category by hand will be listed here.",
  },
  all: { title: "No items yet", message: "Upload a receipt and its items will appear here." },
};

function purchaseDate(item: ReviewQueueItem): string {
  return item.transaction_date ? DATE_FORMAT.format(new Date(item.transaction_date)) : "—";
}

/**
 * The categorisation review queue: items the agent filed under Uncategorized
 * because it was not confident, oldest purchase first (BRD C2-C4 — F5.3, F5.4).
 *
 * Picking a category files the item for good and drops it from the queue; the
 * "Corrected by you" and "All items" views show the rest of the user's items
 * (docs/design/screens/categorisation.html).
 */
export const CategorisationQueuePage = observer(function CategorisationQueuePage() {
  const { categoriesStore } = useStores();
  const { reviewQueue, isLoadingQueue, queueError, queueView, queueSearch } = categoriesStore;
  const empty = queueSearch.trim()
    ? { title: "No matching items", message: `Nothing here is named like “${queueSearch}”.` }
    : EMPTY_MESSAGES[queueView];

  useEffect(() => {
    void categoriesStore.fetchReviewQueue();
  }, [categoriesStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-10 px-4 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-6">
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[28px] font-bold tracking-[-0.02em] text-foreground">
              Categories
            </h1>
            <p className="m-0 text-lg text-muted-foreground">
              Items the agent was not confident about, oldest first.
            </p>
          </div>
          <Link
            to="/categories/manage"
            className="inline-flex items-center gap-2 text-lg font-semibold text-primary hover:text-primary-hover"
          >
            <SlidersHorizontal size={16} aria-hidden="true" />
            Manage the taxonomy
          </Link>
        </header>

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <SegmentedControl<ItemView>
            label="Which items to show"
            size="sm"
            value={queueView}
            onChange={(view) => {
              categoriesStore.setQueueView(view);
            }}
            options={[
              {
                value: "needs_review",
                label: "Needs review",
                badge: categoriesStore.needsReviewCount,
              },
              { value: "corrected", label: "Corrected by you" },
              { value: "all", label: "All items" },
            ]}
          />
          <div className="relative w-full md:w-60">
            <Search
              size={16}
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              className="pl-9 py-2.25 text-md"
              type="search"
              placeholder="Find an item"
              aria-label="Find an item"
              value={queueSearch}
              onChange={(e) => {
                categoriesStore.setQueueSearch(e.target.value);
              }}
            />
          </div>
        </div>

        {isLoadingQueue && reviewQueue.length === 0 ? (
          <LoadingState title="Loading the review queue…" />
        ) : queueError ? (
          <ErrorState
            layout="banner"
            title="The review queue could not be loaded"
            message={queueError}
          />
        ) : reviewQueue.length === 0 ? (
          <Card className="py-12 px-6">
            <EmptyState
              icon={CheckCircle2}
              iconTone="primary"
              title={empty.title}
              message={empty.message}
            />
          </Card>
        ) : (
          <Card flush>
            <div
              aria-hidden="true"
              className="hidden md:grid md:grid-cols-[minmax(0,1fr)_150px_110px_100px_210px] gap-x-4 px-4.5 py-3 bg-surface border-b border-border text-sm font-semibold uppercase tracking-[0.05em] text-muted-foreground"
            >
              <span>Item</span>
              <span>Merchant</span>
              <span>Date</span>
              <span className="text-right">Amount</span>
              <span>Category</span>
            </div>
            <ul className="m-0 p-0 list-none">
              {reviewQueue.map((item) => (
                <li
                  key={item.id}
                  className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 px-4 py-3.5 border-t border-border first:border-t-0 md:grid-cols-[minmax(0,1fr)_150px_110px_100px_210px] md:items-center md:px-4.5"
                >
                  <span className="text-lg font-semibold">{item.name}</span>
                  <span className="order-3 col-span-2 text-md text-muted-foreground md:order-none md:col-span-1">
                    {item.merchant_name ?? "—"}
                    <span className="md:hidden"> · {purchaseDate(item)}</span>
                  </span>
                  <span className="hidden md:block tabular-nums text-md text-muted-foreground">
                    {purchaseDate(item)}
                  </span>
                  <span className="order-2 tabular-nums text-right text-lg font-semibold md:order-none">
                    {Number(item.total_price).toFixed(2)}
                  </span>
                  <div className="order-4 col-span-2 md:order-none md:col-span-1">
                    <InlineCategoryPicker
                      itemId={item.id}
                      itemName={item.name}
                      currentCategoryId={item.category_id}
                      lowConfidence={item.category_is_low_confidence}
                      onCategoryChanged={() => {
                        void categoriesStore.fetchReviewQueue();
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
});

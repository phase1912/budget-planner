import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Search, SlidersHorizontal } from "lucide-react";

import { useStores } from "@/stores/StoreContext";
import {
  Card,
  EmptyState,
  DateRangeFilter,
  ErrorState,
  Input,
  LoadingState,
  Note,
  Pagination,
  Pill,
  SegmentedControl,
} from "@/shared/components";
import { SectionTabs } from "@/features/app-shell/SectionTabs";
import { formatPurchase } from "@/shared/purchaseDate";
import type { ItemView, ReviewQueueItem } from "@/stores/CategoriesStore";
import { CategorySpendList } from "../components/CategorySpendList";
import { InlineCategoryPicker } from "../components/InlineCategoryPicker";
import { numberFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";
import { formatAmount } from "@/i18n/format";

const AMOUNT = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function purchaseDate(item: ReviewQueueItem): string {
  return item.transaction_date
    ? formatPurchase(item.transaction_date, { day: "numeric", month: "short" })
    : "—";
}

const VIEWS: readonly ItemView[] = ["needs_review", "corrected", "all"];
const DAY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * The selection a link asks for, e.g. the dashboard's "Where it went":
 * `?view=all&category=…&start=YYYY-MM-DD&end=YYYY-MM-DD`. Null when the address
 * names none, so the screen keeps whatever the user last chose.
 */
function selectionFrom(params: URLSearchParams) {
  const view = VIEWS.find((v) => v === params.get("view"));
  if (!view) return null;
  const start = params.get("start");
  const end = params.get("end");
  const dated = start !== null && end !== null && DAY.test(start) && DAY.test(end);
  return {
    view,
    categoryId: params.get("category"),
    start: dated ? start : undefined,
    end: dated ? end : undefined,
  };
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
  const { categoriesStore, authStore } = useStores();
  const { t } = useTranslation("categories");
  const { reviewQueue, isLoadingQueue, queueError, queueView, queueSearch } = categoriesStore;
  const filtered =
    queueSearch.trim() !== "" ||
    categoriesStore.queueStartDate !== undefined ||
    categoriesStore.queueCategoryId !== null;
  const currency = authStore.user?.currency ?? "PLN";
  const emptyKind = filtered ? "filtered" : queueView;
  const empty = {
    title: t(`queue.empty.${emptyKind}.title`),
    message: t(`queue.empty.${emptyKind}.message`),
  };

  const [searchParams] = useSearchParams();
  const query = searchParams.toString();

  useEffect(() => {
    const requested = selectionFrom(new URLSearchParams(query));
    if (requested) {
      categoriesStore.showSelection(requested);
      return;
    }
    void categoriesStore.fetchReviewQueue();
  }, [categoriesStore, query]);

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-6">
        <SectionTabs />
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[24px] md:text-[28px] font-bold tracking-[-0.02em] text-foreground">
              {t("queue.title")}
            </h1>
            <p className="m-0 text-lg text-muted-foreground">{t(`queue.subtitle.${queueView}`)}</p>
          </div>
          <Link
            to="/categories/manage"
            className="inline-flex items-center gap-2 text-lg font-semibold text-primary hover:text-primary-hover"
          >
            <SlidersHorizontal size={16} aria-hidden="true" />
            {t("queue.manage")}
          </Link>
        </header>

        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <SegmentedControl<ItemView>
            label={t("queue.which")}
            size="sm"
            fill
            value={queueView}
            onChange={(view) => {
              categoriesStore.setQueueView(view);
            }}
            options={[
              {
                value: "needs_review",
                label: t("queue.views.needsReview"),
                shortLabel: t("queue.views.needsReviewShort"),
                badge: categoriesStore.needsReviewCount,
              },
              {
                value: "corrected",
                label: t("queue.views.corrected"),
                shortLabel: t("queue.views.correctedShort"),
              },
              {
                value: "all",
                label: t("queue.views.all"),
                shortLabel: t("queue.views.allShort"),
              },
            ]}
          />
          <div className="flex items-center gap-2.5">
            <DateRangeFilter
              start={categoriesStore.queueStartDate}
              end={categoriesStore.queueEndDate}
              onApply={(start, end) => {
                categoriesStore.setQueueDates(start, end);
              }}
            />
            <div className="relative w-full lg:w-60">
              <Search
                size={16}
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                className="pl-9 py-2.25 text-md"
                type="search"
                placeholder={t("queue.find")}
                aria-label={t("queue.find")}
                value={queueSearch}
                onChange={(e) => {
                  categoriesStore.setQueueSearch(e.target.value);
                }}
              />
            </div>
          </div>
        </div>

        {!queueError && (
          <CategorySpendList
            spend={categoriesStore.queueCategorySpend}
            selectedId={categoriesStore.queueCategoryId}
            onSelect={(categoryId) => {
              categoriesStore.setQueueCategory(categoryId);
            }}
          />
        )}

        {isLoadingQueue && reviewQueue.length === 0 ? (
          <LoadingState title={t("queue.loading")} />
        ) : queueError ? (
          <ErrorState layout="banner" title={t("queue.loadFailed")} message={queueError} />
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
              className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_150px_110px_100px_210px] gap-x-4 px-4.5 py-3 bg-surface border-b border-border text-sm font-semibold uppercase tracking-[0.05em] text-muted-foreground"
            >
              <span>{t("queue.cols.item")}</span>
              <span>{t("queue.cols.merchant")}</span>
              <span>{t("queue.cols.date")}</span>
              <span className="text-right">{t("queue.cols.amount")}</span>
              <span>{t("queue.cols.category")}</span>
            </div>
            <ul className="m-0 p-0 list-none">
              {reviewQueue.map((item) => (
                <li
                  key={item.id}
                  className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 px-4 py-3.5 border-t border-border first:border-t-0 lg:grid-cols-[minmax(0,1fr)_150px_110px_100px_210px] lg:items-center md:px-4.5"
                >
                  <span className="flex flex-wrap items-center gap-2 text-lg font-semibold">
                    {item.name}
                    {item.receipt_status === "manual_review" && (
                      <Pill tone="warning" size="sm" title={t("queue.underReviewTitle")}>
                        {t("queue.underReview")}
                      </Pill>
                    )}
                  </span>
                  <span className="order-3 col-span-2 text-md text-muted-foreground lg:order-none lg:col-span-1">
                    {item.merchant_name ?? "—"}
                    <span className="lg:hidden"> · {purchaseDate(item)}</span>
                  </span>
                  <span className="hidden lg:block tabular-nums text-md text-muted-foreground">
                    {purchaseDate(item)}
                  </span>
                  <span className="order-2 tabular-nums text-right text-lg font-semibold lg:order-none">
                    {formatAmount(item.total_price)}
                  </span>
                  <div className="order-4 col-span-2 lg:order-none lg:col-span-1">
                    <InlineCategoryPicker
                      itemId={item.id}
                      itemName={item.name}
                      merchantName={item.merchant_name}
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
            <p className="m-0 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3.5 border-t border-border bg-surface md:px-4.5">
              <span className="text-md text-muted-foreground">
                {t("items", { count: categoriesStore.queueTotal })}
                {categoriesStore.queueExcludedCount > 0 &&
                  t("queue.excluded", {
                    count: categoriesStore.queueExcludedCount,
                    amount: AMOUNT.format(Number(categoriesStore.queueExcludedAmount)),
                    currency,
                  })}
              </span>
              <span className="tabular-nums text-lg font-bold">
                {AMOUNT.format(Number(categoriesStore.queueTotalAmount))} {currency}
              </span>
            </p>
          </Card>
        )}

        {categoriesStore.queueTotal > 0 && (
          <Pagination
            page={categoriesStore.queuePage}
            pages={categoriesStore.queuePages}
            size={categoriesStore.queueSize}
            total={categoriesStore.queueTotal}
            onPageChange={(page) => {
              categoriesStore.setQueuePage(page);
            }}
          />
        )}

        <Note tone="accent">{t("queue.rule")}</Note>
      </div>
    </div>
  );
});

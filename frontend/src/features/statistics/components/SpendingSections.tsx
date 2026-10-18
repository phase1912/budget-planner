import { observer } from "mobx-react-lite";
import { ChevronRight, House } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Collapsible } from "@/shared/components";
import { InlineCategoryPicker } from "@/features/categories/components/InlineCategoryPicker";
import { dateFormat, formatAmount, numberFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";

const DAY = dateFormat({ day: "numeric", month: "short" });
const WHOLE = numberFormat({ maximumFractionDigits: 0 });

/**
 * The period's receipts, opened in place on Spending (F23.4): newest first, a tap opens
 * one; the Receipts page stays one link away for search and filters.
 */
export const PeriodReceipts = observer(function PeriodReceipts() {
  const { statisticsStore, receiptStore } = useStores();
  const { t } = useTranslation("statistics");
  const { start, end, statistics, receipts, receiptCount, isLoadingReceipts } = statisticsStore;
  return (
    <Collapsible
      title={t("sections.receipts")}
      aside={statistics?.receipt_count ?? undefined}
      onOpen={() => {
        void statisticsStore.loadReceipts();
      }}
    >
      {isLoadingReceipts && receipts.length === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("sections.loading")}</p>
      ) : receipts.length === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("sections.noReceipts")}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-control control-fill p-0">
          {receipts.map((receipt) => (
            <li key={receipt.id}>
              <button
                type="button"
                onClick={() => void receiptStore.fetchReceiptDetail(receipt.id)}
                className="flex min-h-14 w-full items-center gap-3 px-3.5 py-2 text-left"
              >
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-lg font-semibold">
                    {receipt.merchant_name ?? t("sections.unknownShop")}
                  </span>
                  <span className="text-md text-muted-foreground">
                    {DAY.format(new Date(receipt.transaction_date ?? receipt.created_at))}
                    {receipt.status !== "parsed" && ` · ${t("sections.toCheck")}`}
                  </span>
                </span>
                <span className="text-lg font-bold tabular-nums">
                  {receipt.total_amount ? formatAmount(receipt.total_amount) : "—"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <Link
        to={`/receipts?start=${start}&end=${end}`}
        className="flex min-h-11 items-center justify-between text-lg font-bold text-primary"
      >
        {receiptCount > receipts.length
          ? t("sections.allReceipts", { count: receiptCount })
          : t("sections.searchReceipts")}
        <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </Collapsible>
  );
});

/**
 * Items the reader was unsure of, filed in place on Spending (C3 — F23.4): pick a
 * category and the item leaves the list; the full queue stays one link away.
 */
export const ItemsToFile = observer(function ItemsToFile() {
  const { categoriesStore } = useStores();
  const { t } = useTranslation("statistics");
  const count = categoriesStore.reviewCount;
  if (count === 0) return null;
  return (
    <Collapsible
      title={t("sections.toFile")}
      aside={count}
      onOpen={() => {
        void categoriesStore.fetchReviewQueue();
      }}
    >
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {categoriesStore.reviewQueue.slice(0, 8).map((item) => (
          <li key={item.id} className="flex flex-col gap-2 rounded-control control-fill p-3">
            <span className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 break-words text-lg font-semibold">{item.name}</span>
              <span className="shrink-0 text-lg font-bold tabular-nums">
                {formatAmount(item.total_price)}
              </span>
            </span>
            <span className="text-md text-muted-foreground">{item.merchant_name ?? "—"}</span>
            <InlineCategoryPicker
              itemId={item.id}
              itemName={item.name}
              merchantName={item.merchant_name}
              currentCategoryId={item.category_id}
              lowConfidence={item.category_is_low_confidence}
              onCategoryChanged={() => {
                void categoriesStore.fetchReviewQueue();
                void categoriesStore.loadReviewCount();
              }}
            />
          </li>
        ))}
      </ul>
      <Link
        to="/categories"
        className="flex min-h-11 items-center justify-between text-lg font-bold text-primary"
      >
        {t("sections.allItems")}
        <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </Collapsible>
  );
});

/** The bills that go every month without a receipt (F23.18), as part of what is spent. */
export const RegularBills = observer(function RegularBills({ currency }: { currency: string }) {
  const { incomeStore } = useStores();
  const { t } = useTranslation("statistics");
  const bills = incomeStore.bills;
  if (bills.length === 0) return null;
  const total = bills.reduce((sum, bill) => sum + Number(bill.amount), 0);
  return (
    <Collapsible title={t("sections.bills")} aside={`${WHOLE.format(total)} ${currency}`}>
      <p className="m-0 text-md text-muted-foreground">{t("sections.billsHint")}</p>
      <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
        {bills.map((bill) => (
          <li key={bill.id} className="flex min-h-12 items-center gap-3">
            <House size={18} aria-hidden="true" className="text-muted-foreground" />
            <span className="flex-1 text-lg font-semibold">{bill.name}</span>
            <span className="text-lg font-bold tabular-nums">
              {WHOLE.format(Number(bill.amount))} {currency}
            </span>
          </li>
        ))}
      </ul>
    </Collapsible>
  );
});

import { ChevronRight, TriangleAlert } from "lucide-react";
import { Link } from "react-router-dom";

import { Card } from "@/shared/components";
import { formatPurchase } from "@/shared/purchaseDate";
import type { Receipt } from "@/stores/ReceiptStore";
import { numberFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const AMOUNT = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

interface MonthReceiptsProps {
  /** "Latest receipts" for a running month, "Biggest receipts" for a finished one. */
  title: string;
  receipts: Receipt[];
  /** How many receipts the month holds, for the "All N" link. */
  total: number;
  /** The receipts list narrowed to this month. */
  allHref: string;
  onOpen: (id: string) => void;
}

/**
 * The shown month's receipts column, each opening its detail dialog in place:
 * the newest of a running month (docs/design/screens/dashboard.html), the
 * biggest of a finished one (dashboard-dark.html). Correcting one from there
 * moves the month figure above without leaving the page (BRD D6 — F6.5).
 *
 * A receipt held for review says so instead of its date: it is not in the
 * figure until resolved (D3).
 */
export function MonthReceipts({ title, receipts, total, allHref, onOpen }: MonthReceiptsProps) {
  const { t } = useTranslation("dashboard");
  return (
    <Card variant="default" className="flex h-full flex-col px-6 py-5.5">
      <div className="mb-3.5 flex items-baseline justify-between gap-4">
        <h2 className="m-0 text-[16px] font-bold">{title}</h2>
        {total > 0 && (
          <Link to={allHref} className="text-md">
            {t("receiptsCard.all", { count: total })}
          </Link>
        )}
      </div>
      {receipts.length === 0 ? (
        <p className="m-0 py-3 text-md text-muted-foreground">{t("receiptsCard.none")}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col p-0">
          {receipts.map((receipt) => (
            <li key={receipt.id} className="border-t border-muted first:border-t-0">
              <ReceiptRow
                receipt={receipt}
                onOpen={() => {
                  onOpen(receipt.id);
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ReceiptRow({ receipt, onOpen }: { receipt: Receipt; onOpen: () => void }) {
  const { t } = useTranslation("dashboard");
  const underReview = receipt.status === "manual_review";
  const items = t("receiptsCard.items", { count: receipt.line_items.length });
  const bought = receipt.transaction_date
    ? formatPurchase(receipt.transaction_date, { day: "numeric", month: "short" })
    : t("receiptsCard.noDate");
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full cursor-pointer items-center justify-between gap-3 py-3 text-left"
    >
      <span className="flex min-w-0 flex-grow flex-col gap-0.75">
        <span className="flex items-center gap-1.75 truncate text-md font-semibold">
          {receipt.merchant_name ?? t("receiptsCard.unknownMerchant")}
          {underReview && (
            <TriangleAlert
              size={13}
              aria-hidden="true"
              className="shrink-0 text-tone-warning-text"
            />
          )}
        </span>
        {underReview ? (
          <span className="text-base text-tone-warning-text">{t("receiptsCard.review")}</span>
        ) : (
          <span className="tabular-nums text-base text-muted-foreground">
            {bought} · {items}
          </span>
        )}
      </span>
      <span
        className={`tabular-nums text-lg font-semibold ${underReview ? "text-muted-foreground" : ""}`}
      >
        {receipt.total_amount ? AMOUNT.format(Number(receipt.total_amount)) : "—"}
      </span>
      <ChevronRight size={15} aria-hidden="true" className="shrink-0 text-muted-foreground" />
    </button>
  );
}

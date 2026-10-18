import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { formatPurchase } from "@/shared/purchaseDate";
import { numberFormat } from "@/i18n/format";
import type { Receipt } from "@/stores/ReceiptStore";

const AMOUNT = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });
const TINTS = [
  "var(--cat-groceries)",
  "var(--cat-dining)",
  "var(--cat-transport)",
  "var(--cat-utilities)",
  "var(--cat-health)",
  "var(--cat-entertainment)",
];

/** A shop's colour, the same every time it appears. */
function shopColor(name: string): string {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return TINTS[hash % TINTS.length] ?? "var(--cat-other)";
}

interface RecentPurchasesProps {
  title: string;
  receipts: Receipt[];
  total: number;
  allHref: string;
  onOpen: (id: string) => void;
}

/**
 * The month's receipts on Home (F23.3, F6.7): the newest of a running month, the biggest
 * of a finished one, each with its shop's initial in the shop's colour, opening its detail
 * in place. A receipt held for review says so instead of its date and is not in the month
 * (D3).
 */
export function RecentPurchases({ title, receipts, total, allHref, onOpen }: RecentPurchasesProps) {
  const { t } = useTranslation("dashboard");
  return (
    <section aria-labelledby="recent" className="flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between">
        <h2 id="recent" className="m-0 text-xl font-extrabold">
          {title}
        </h2>
        {total > 0 && (
          <Link to={allHref} className="text-md font-bold text-primary">
            {t("receiptsCard.all", { count: total })}
          </Link>
        )}
      </div>
      {receipts.length === 0 ? (
        <p className="m-0 rounded-card bg-surface p-4 text-md text-muted-foreground">
          {t("receiptsCard.none")}
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col divide-y divide-border overflow-hidden rounded-card bg-surface p-0">
          {receipts.map((receipt) => {
            const name = receipt.merchant_name ?? t("receiptsCard.unknownMerchant");
            const color = shopColor(name);
            const review = receipt.status === "manual_review";
            const bought = receipt.transaction_date
              ? formatPurchase(receipt.transaction_date, { day: "numeric", month: "short" })
              : t("receiptsCard.noDate");
            return (
              <li key={receipt.id}>
                <button
                  type="button"
                  onClick={() => {
                    onOpen(receipt.id);
                  }}
                  className="flex min-h-16 w-full items-center gap-3 px-3.5 py-3 text-left"
                >
                  <span
                    aria-hidden="true"
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-pill text-lg font-extrabold"
                    style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}
                  >
                    {name.charAt(0).toUpperCase()}
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-lg font-bold">{name}</span>
                    <span
                      className={`text-base ${review ? "text-tone-warning-text" : "text-muted-foreground"}`}
                    >
                      {review
                        ? t("receiptsCard.review")
                        : `${bought} · ${t("receiptsCard.items", { count: receipt.line_items.length })}`}
                    </span>
                  </span>
                  <span
                    className={`text-lg font-extrabold tabular-nums ${review ? "text-muted-foreground" : ""}`}
                  >
                    {receipt.total_amount ? AMOUNT.format(Number(receipt.total_amount)) : "—"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

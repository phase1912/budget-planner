import { useEffect, useState } from "react";
import { Mail, PenLine } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import type { components } from "@/api/schema";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { DeleteReceiptDialog } from "../components/DeleteReceiptDialog";
import { EditReceiptDialog } from "../components/EditReceiptDialog";
import { ReceiptDetailModal } from "../components/ReceiptDetailModal";
import { DateFilterModal, ReceiptOrderControl } from "../components/DateFilterModal";
import { StatusFilterDropdown } from "../components/StatusFilterDropdown";
import { ChannelFilterDropdown } from "../components/ChannelFilterDropdown";
import { Button, Card, Input, IconTile, Pagination, SegmentedControl } from "@/shared/components";
import { ManualExpenseDialog } from "../components/ManualExpenseDialog";
import { TripLabel } from "@/features/trips/components/TripLabel";
import { SectionTabs } from "@/features/app-shell/SectionTabs";
import { ExportMenu } from "@/features/exports/components/ExportMenu";
import { formatPurchase } from "@/shared/purchaseDate";
import { useTranslation } from "react-i18next";
import { formatAmount } from "@/i18n/format";

type ReceiptStatus = components["schemas"]["ReceiptStatus"];

const STATUSES: readonly ReceiptStatus[] = [
  "uploaded",
  "parsing",
  "parsed",
  "manual_review",
  "failed",
];

function isReceiptStatus(value: string | null): value is ReceiptStatus {
  return STATUSES.some((status) => status === value);
}

const DAY = /^\d{4}-\d{2}-\d{2}$/;

export const ReceiptsPage = observer(() => {
  const { receiptStore, exportStore, householdStore, authStore } = useStores();
  const [addingExpense, setAddingExpense] = useState(false);
  const { t } = useTranslation(["receipts", "common"]);
  const household = householdStore.household;
  // A household of one has nothing to share yet, so the switch waits for a second member.
  const shared = household !== null && household.members.length > 1;
  const showingHousehold = shared && receiptStore.scope === "household";
  const ownerName = (userId: string): string | null =>
    userId === authStore.user?.id
      ? null
      : (household?.members.find((m) => m.user_id === userId)?.first_name ??
        t("list.formerMember"));

  useEffect(() => {
    void householdStore.load();
  }, [householdStore]);

  useEffect(() => {
    // Left the household, or the other member did: there is nothing shared to show.
    if (householdStore.loaded && !shared && receiptStore.scope === "household") {
      receiptStore.setScope("mine");
    }
  }, [householdStore.loaded, shared, receiptStore]);
  const [searchParams] = useSearchParams();
  const requestedStatus = searchParams.get("status");
  const requestedStart = searchParams.get("start");
  const requestedEnd = searchParams.get("end");
  const requestedSearch = searchParams.get("q");

  useEffect(() => {
    // `?status=manual_review` is how the dashboard's "Resolve them" opens this
    // list already narrowed to the receipts held out of the month (BRD D3).
    if (isReceiptStatus(requestedStatus)) {
      receiptStore.setFilters({ status: requestedStatus });
      return;
    }
    // `?start=…&end=…` is the dashboard's "All N": every receipt of one month; with `q`,
    // the assistant's link to the receipts it answered about (F21.4).
    if (requestedStart && requestedEnd && DAY.test(requestedStart) && DAY.test(requestedEnd)) {
      receiptStore.setFilters({
        status: undefined,
        startDate: requestedStart,
        endDate: requestedEnd,
        searchQuery: requestedSearch ?? undefined,
      });
      return;
    }
    void receiptStore.fetchReceipts(receiptStore.page, receiptStore.size);
  }, [receiptStore, requestedStatus, requestedStart, requestedEnd, requestedSearch]);

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[960px] flex flex-col gap-4 md:gap-7">
        <SectionTabs />
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em] text-foreground">
              {t("list.title")}
            </h1>
            <p className="m-0 text-md text-muted-foreground tabular-nums">
              {t("list.stored", { count: receiptStore.total })}
            </p>
          </div>
          {/* An export is the user's own data (N6); the household view has none to offer. */}
          {!showingHousehold && (
            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                aria-label={t("manual.openLong")}
                className="h-11 w-11 p-0 md:w-auto md:px-3.5"
                onClick={() => {
                  setAddingExpense(true);
                }}
              >
                <PenLine size={16} aria-hidden="true" />
                <span className="hidden md:inline">{t("manual.open")}</span>
              </Button>
              <ExportMenu
                compact
                label={t("list.export")}
                busy={Boolean(exportStore.busy.receipts)}
                onExport={(format) => {
                  // The file holds the list as filtered on screen (BRD N6).
                  void exportStore.start({
                    kind: "receipts",
                    format,
                    start: receiptStore.startDateFilter ?? null,
                    end: receiptStore.endDateFilter ?? null,
                    status: receiptStore.statusFilter ?? null,
                    q: receiptStore.searchQuery ?? null,
                    compare: false,
                  });
                }}
              />
            </div>
          )}
        </div>
        {shared && (
          <SegmentedControl
            label={t("list.whose")}
            value={receiptStore.scope}
            onChange={(scope) => {
              receiptStore.setScope(scope);
            }}
            fill
            options={[
              { value: "mine", label: t("common:mine") },
              { value: "household", label: household.name, shortLabel: t("common:household") },
            ]}
          />
        )}

        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between lg:gap-4">
          <div className="flex flex-wrap items-center gap-2.5">
            <DateFilterModal />
            <ReceiptOrderControl />
            <div className="grid w-full grid-cols-2 gap-2 md:flex md:w-auto">
              <StatusFilterDropdown />
              <ChannelFilterDropdown />
            </div>
          </div>
          <div className="relative w-full lg:w-[250px]">
            <svg
              className="absolute left-3.5 top-4 text-muted-foreground pointer-events-none"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <Input
              className="w-full pl-10"
              type="search"
              placeholder={t("list.search")}
              aria-label={t("list.searchLabel")}
              value={receiptStore.searchQuery ?? ""}
              onChange={(e) => {
                receiptStore.setFilters({ searchQuery: e.target.value || undefined });
              }}
            />
          </div>
        </div>

        <Card flush>
          <div className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_120px_92px_120px_170px_28px] items-center gap-4 px-[18px] py-[12px] bg-surface border-b border-border">
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
              {t("list.cols.merchant")}
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
              {t("list.cols.date")}
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
              {t("list.cols.items")}
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
              {t("list.cols.total")}
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
              {t("list.cols.status")}
            </span>
            <span></span>
          </div>

          {receiptStore.isLoadingList ? (
            <div className="p-[18px] text-center text-muted-foreground">{t("list.loading")}</div>
          ) : receiptStore.receipts.length === 0 ? (
            <div className="p-[18px] text-center text-muted-foreground">{t("list.empty")}</div>
          ) : (
            receiptStore.receipts.map((receipt) => {
              const isParsed = receipt.status === "parsed";
              const isFailed = receipt.status === "failed";
              const isReview = receipt.status === "manual_review";
              // F20.1: read, but the employer's money: out of the total, owed back.
              const isRepaid = isParsed && receipt.trip?.kind === "business";

              let rowBg = "hover:bg-surface";
              if (isFailed) rowBg = "bg-tone-error-bg";
              else if (isReview) rowBg = "bg-tone-warning-bg";

              return (
                <button
                  key={receipt.id}
                  className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 px-4 py-3 w-full text-left border-b border-border last:border-0 cursor-pointer transition-colors lg:grid-cols-[minmax(0,1fr)_120px_92px_120px_170px_28px] lg:gap-4 lg:px-[18px] lg:py-[14px] ${rowBg}`}
                  onClick={() => {
                    void receiptStore.fetchReceiptDetail(receipt.id);
                  }}
                >
                  <span className="flex min-w-0 items-center gap-[11px] text-[14px] font-semibold text-foreground">
                    <IconTile
                      tone={
                        isParsed ? "success" : isFailed ? "error" : isReview ? "warning" : "default"
                      }
                      size="sm"
                    >
                      {isFailed ? (
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
                          <path d="M12 9v4" />
                          <path d="M12 17h.01" />
                        </svg>
                      ) : receipt.channel === "email" ? (
                        <Mail size={15} role="img" aria-label={t("list.fromEmail")} />
                      ) : receipt.channel === "manual" ? (
                        <PenLine size={15} role="img" aria-label={t("list.manual")} />
                      ) : (
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
                          <path d="M16 8H8" />
                          <path d="M16 12H8" />
                        </svg>
                      )}
                    </IconTile>
                    {/* F20.1: under the name, the trip it is on or a business trip asking about it. */}
                    <span className="flex min-w-0 flex-col items-start gap-0.5">
                      <span className="max-w-full truncate">
                        {receipt.merchant_name ?? t("list.unknownMerchant")}
                      </span>
                      <TripLabel trip={receipt.trip} question={receipt.trip_question} />
                    </span>
                    {/* F12.4: in the household view, whose each receipt is, and which of mine it does not see. */}
                    {showingHousehold && ownerName(receipt.user_id) && (
                      <span className="shrink-0 text-[12px] font-normal text-muted-foreground">
                        {ownerName(receipt.user_id)}
                      </span>
                    )}
                    {showingHousehold && receipt.is_private && (
                      <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[12px] font-semibold text-muted-foreground">
                        {t("list.private")}
                      </span>
                    )}
                    {/* F11.5: an emailed receipt alike to a stored one waits for the user. */}
                    {receipt.possible_duplicate_of_id && (
                      <span className="shrink-0 rounded-full bg-tone-warning-bg px-2 py-0.5 text-[12px] font-semibold text-tone-warning-text">
                        {t("list.duplicate")}
                      </span>
                    )}
                  </span>
                  <span className="order-2 pl-[41px] tabular-nums text-muted-foreground text-[12px] lg:order-none lg:pl-0 lg:text-[13px]">
                    {receipt.transaction_date
                      ? formatPurchase(receipt.transaction_date, {
                          day: "numeric",
                          month: "short",
                        }) +
                        // An expense typed in has a day, never a time (F20.5).
                        (receipt.channel === "manual"
                          ? ""
                          : ", " +
                            formatPurchase(receipt.transaction_date, {
                              hour: "2-digit",
                              minute: "2-digit",
                            }))
                      : t("list.unknownDate")}
                    {/* Below lg there is no items column; the count joins the date. */}
                    <span className="lg:hidden">
                      {" · "}
                      {t("list.items", { count: receipt.line_items.length })}
                    </span>
                  </span>
                  <span className="hidden lg:block tabular-nums text-muted-foreground text-right text-[13px]">
                    {receipt.line_items.length}
                  </span>
                  <span className="order-1 flex flex-col items-end tabular-nums text-right text-[14px] font-semibold text-foreground lg:order-none">
                    {receipt.total_amount ? formatAmount(receipt.total_amount) : "—"}
                    {/* F11.7: converted from another currency, which the row names. */}
                    {receipt.original_currency && receipt.original_total && (
                      <span className="text-[12px] font-normal text-muted-foreground">
                        {t(receipt.exchange_rate ? "list.convertedFrom" : "list.unconvertedIn", {
                          amount: formatAmount(receipt.original_total),
                          currency: receipt.original_currency,
                        })}
                      </span>
                    )}
                  </span>
                  <span className="order-3 justify-self-end lg:order-none lg:justify-self-auto">
                    <span
                      className={`inline-flex items-center gap-[6px] rounded-full px-[11px] py-[5px] text-[12px] font-semibold whitespace-nowrap ${
                        isRepaid
                          ? "bg-tone-info-bg text-tone-info-text"
                          : isParsed
                            ? "bg-tone-primary-bg text-tone-primary-text"
                            : isFailed
                              ? "bg-tone-error-bg text-tone-error-text"
                              : isReview
                                ? "bg-tone-warning-bg text-tone-warning-text"
                                : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {isParsed && (
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                      {isFailed && (
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
                          <path d="M12 9v4" />
                          <path d="M12 17h.01" />
                        </svg>
                      )}
                      {isReview && (
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <circle cx="12" cy="12" r="10" />
                          <path d="M12 8v4" />
                          <path d="M12 16h.01" />
                        </svg>
                      )}
                      {isRepaid
                        ? t("status.repaid")
                        : isParsed
                          ? t("status.inTotal")
                          : isFailed
                            ? t("status.outOfTotal")
                            : isReview
                              ? t("status.review")
                              : receipt.status}
                    </span>
                  </span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="hidden text-muted-foreground lg:block"
                  >
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                </button>
              );
            })
          )}
        </Card>

        <div className="mt-4">
          <Pagination
            page={receiptStore.page}
            pages={receiptStore.pages}
            size={receiptStore.size}
            total={receiptStore.total}
            onPageChange={(page) => {
              void receiptStore.fetchReceipts(page, receiptStore.size);
            }}
          />
        </div>

        {receiptStore.selectedReceiptId && <ReceiptDetailModal />}
        {addingExpense && (
          <ManualExpenseDialog
            onClose={() => {
              setAddingExpense(false);
            }}
          />
        )}
        <DeleteReceiptDialog />
        <EditReceiptDialog />
      </div>
    </div>
  );
});

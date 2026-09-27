import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { ArrowRight, ChevronRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { useStores } from "@/stores/StoreContext";
import { monthRange } from "@/stores/BudgetStore";
import type { MonthSummary } from "@/stores/BudgetStore";
import { Card, ErrorState, LoadingState, Note } from "@/shared/components";
import { DeleteReceiptDialog } from "@/features/receipts/components/DeleteReceiptDialog";
import { EditReceiptDialog } from "@/features/receipts/components/EditReceiptDialog";
import { ReceiptDetailModal } from "@/features/receipts/components/ReceiptDetailModal";
import { CategorySpendList } from "@/features/categories/components/CategorySpendList";
import { LimitStatus } from "../components/LimitStatus";
import { MonthReceipts } from "../components/MonthReceipts";
import { MonthStatus } from "../components/MonthStatus";
import { MonthSwitcher } from "../components/MonthSwitcher";
import { TopCategories } from "../components/TopCategories";
import { WelcomePanel } from "../components/WelcomePanel";

const MONTH_AND_YEAR = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" });
const MONTH = new Intl.DateTimeFormat("en-GB", { month: "long" });
const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * The landing view (docs/design/screens/dashboard.html): the month's spend by
 * receipt date, with a switcher to step back through earlier months (BRD D1,
 * D2 — F6.1). A user with no receipts yet sees the welcome instead.
 *
 * Receipts under manual review are left out of the figure and named beneath
 * it, with the way through to fix them (D3 — F6.2). An unfinished month is
 * labelled month-to-date, with the days so far (D4 — F6.3).
 *
 * Beneath it, where the month went by category, and its receipts, which open
 * their detail dialog here; correcting or deleting one refetches the month, so
 * its figure moves without a reload, and the view reopens on the month it was
 * left on (D6 — F6.5). Where the user has set a monthly limit, the figure reads
 * as a share of it, past 100% when over (D7 — F6.6).
 *
 * All of it arrives in one request, and "Full statistics" leads on to E7 (F6.7).
 * A phone gets docs/design/screens/dashboard-mobile.html: the month centred
 * between its arrows, the shorter figure card, the held-out receipts as one
 * tappable line, and the top five categories in place of the breakdown and the
 * receipts column.
 */
export const DashboardPage = observer(function DashboardPage() {
  const { budgetStore, authStore, receiptStore } = useStores();
  const { summary, isLoading, error } = budgetStore;
  const navigate = useNavigate();

  useEffect(() => {
    void budgetStore.open();
  }, [budgetStore]);

  if (!summary) {
    return (
      <div className="flex-grow flex flex-col items-center py-10 px-4 md:px-8">
        <div className="w-full max-w-[960px]">
          {error ? (
            <ErrorState layout="banner" title="The month could not be loaded" message={error} />
          ) : (
            <LoadingState title="Loading your month…" />
          )}
        </div>
      </div>
    );
  }

  if (!summary.has_receipts) return <WelcomePanel />;

  const selected = new Date(budgetStore.year, budgetStore.month - 1, 1);
  // The figure's own month, not the selection: while the next month loads, the
  // old figure stays labelled as what it is.
  const figureMonth = new Date(summary.year, summary.month - 1, 1);
  const currency = authStore.user?.currency ?? "PLN";
  // An unfinished month's figure is month-to-date and must never read as final (D4).
  // A phone drops the month's name, already shown right above the card.
  const wide = (text: string) => <span className="hidden md:inline">{text}</span>;
  const heading = (
    <>
      {summary.is_complete ? "Spent" : "Spent so far"}
      {wide(` in ${MONTH.format(figureMonth)}`)}
    </>
  );
  const limit = limitOf(summary);
  const overLimit = limit !== null && Number(limit.remaining) < 0;
  const days = summary.is_complete ? (
    `${String(summary.days_in_month)} of ${String(summary.days_in_month)} days`
  ) : (
    <>
      {`${String(summary.days_elapsed)} of ${String(summary.days_in_month)} days`}
      {wide(" recorded")}
    </>
  );
  const heldOut =
    summary.excluded_count === 1 ? "1 receipt" : `${String(summary.excluded_count)} receipts`;
  const heldOutWorth = `${heldOut} worth ${AMOUNT.format(Number(summary.excluded_amount))} ${currency}`;

  const meta = (
    <span className="tabular-nums text-sm text-muted-foreground md:text-md">
      {days} ·{" "}
      {summary.receipt_count === 1 ? "1 receipt" : `${String(summary.receipt_count)} receipts`}
      {overLimit && " · the mark is where the limit sat"}
    </span>
  );

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:px-8 md:py-7">
      <div className="w-full max-w-[960px] flex flex-col gap-4 md:gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3.5">
          <div className="flex w-full items-center gap-3.5 md:w-auto">
            <MonthSwitcher
              label={MONTH_AND_YEAR.format(selected)}
              canGoForward={budgetStore.canGoForward}
              onPrevious={() => {
                void budgetStore.showPreviousMonth();
              }}
              onNext={() => {
                void budgetStore.showNextMonth();
              }}
              status={<MonthStatus isComplete={summary.is_complete} compact />}
            />
            <span className="hidden md:inline-flex">
              <MonthStatus isComplete={summary.is_complete} />
            </span>
          </div>
          <Link to="/statistics" className="hidden items-center gap-1.75 text-lg md:inline-flex">
            Full statistics
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>

        {error && (
          <ErrorState layout="banner" title="The month could not be loaded" message={error} />
        )}

        <Card
          variant="surface"
          aria-busy={isLoading}
          className={`flex flex-col gap-3 p-5 md:gap-2.5 md:px-8 md:py-7 transition-opacity ${isLoading ? "opacity-60" : ""}`}
        >
          <span className="text-base font-medium text-muted-foreground md:text-md">{heading}</span>
          <p className="m-0 flex flex-wrap items-baseline gap-2 md:gap-3">
            <span className="tabular-nums text-[36px] font-bold leading-none tracking-[-0.025em] md:text-[46px]">
              {AMOUNT.format(Number(summary.total))}
            </span>
            <span className="text-[16px] font-semibold text-muted-foreground md:text-xl">
              {currency}
            </span>
          </p>
          {limit ? (
            <LimitStatus {...limit} currency={currency}>
              {meta}
            </LimitStatus>
          ) : (
            meta
          )}
        </Card>

        {summary.excluded_count > 0 && (
          <>
            <Link to="/receipts?status=manual_review" className="text-inherit md:hidden">
              <Note tone="warning">
                <span className="flex items-center justify-between gap-3">
                  <span className="tabular-nums">
                    {heldOutWorth} {summary.excluded_count === 1 ? "sits" : "sit"} outside this
                    total.
                  </span>
                  <ChevronRight size={16} aria-hidden="true" className="shrink-0" />
                </span>
              </Note>
            </Link>
            <div className="hidden md:block">
              <Note tone="warning">
                <span className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <span className="tabular-nums">
                    {heldOutWorth} {summary.excluded_count === 1 ? "is" : "are"} not in this total —
                    the date or total could not be read.
                  </span>
                  <Link to="/receipts?status=manual_review" className="shrink-0 underline">
                    {summary.excluded_count === 1 ? "Resolve it" : "Resolve them"}
                  </Link>
                </span>
              </Note>
            </div>
          </>
        )}

        <div className="md:hidden">
          <TopCategories
            spend={budgetStore.spend}
            hrefFor={(categoryId) => categoryItemsHref(summary, categoryId)}
          />
        </div>

        <div className="hidden gap-5 md:grid md:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
          <CategorySpendList
            spend={budgetStore.spend}
            hint="Highest first"
            onSelect={(categoryId) => {
              if (categoryId) void navigate(categoryItemsHref(summary, categoryId));
            }}
          />
          <MonthReceipts
            title={summary.is_complete ? "Biggest receipts" : "Latest receipts"}
            receipts={budgetStore.receipts}
            total={budgetStore.receiptsInMonth}
            allHref={`/receipts?${monthQuery(summary)}`}
            onOpen={(id) => {
              void receiptStore.fetchReceiptDetail(id);
            }}
          />
        </div>

        {receiptStore.selectedReceiptId && <ReceiptDetailModal />}
        <DeleteReceiptDialog />
        <EditReceiptDialog />
      </div>
    </div>
  );
});

/** The figure's month as `start=…&end=…`, how the receipts and categories screens take it. */
function monthQuery(month: { year: number; month: number }): string {
  const { start, end } = monthRange(month);
  return `start=${start.slice(0, 10)}&end=${end.slice(0, 10)}`;
}

/** One category's items in the figure's month, on the categories screen. */
function categoryItemsHref(month: { year: number; month: number }, categoryId: string): string {
  return `/categories?view=all&category=${encodeURIComponent(categoryId)}&${monthQuery(month)}`;
}

/** The month measured against the user's limit, or null when they have not set one (D7). */
function limitOf(summary: MonthSummary) {
  const { budget_limit, limit_percent, limit_remaining } = summary;
  if (budget_limit == null || limit_percent == null || limit_remaining == null) return null;
  return { limit: budget_limit, percent: limit_percent, remaining: limit_remaining };
}

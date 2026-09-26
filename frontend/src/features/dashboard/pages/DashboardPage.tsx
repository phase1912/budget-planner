import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";

import { useStores } from "@/stores/StoreContext";
import { Card, ErrorState, LoadingState, Note } from "@/shared/components";
import { MonthSwitcher } from "../components/MonthSwitcher";
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
 * it, with the way through to fix them (D3 — F6.2). The limit bar, the
 * month-to-date label and the category breakdown arrive with F6.6, F6.3 and F6.7.
 */
export const DashboardPage = observer(function DashboardPage() {
  const { budgetStore, authStore } = useStores();
  const { summary, isLoading, error } = budgetStore;

  useEffect(() => {
    void budgetStore.showCurrentMonth();
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
  const { current } = budgetStore;
  const figureIsCurrent = summary.year === current.year && summary.month === current.month;
  const currency = authStore.user?.currency ?? "PLN";
  const heading = figureIsCurrent
    ? `Spent so far in ${MONTH.format(figureMonth)}`
    : `Spent in ${MONTH.format(figureMonth)}`;

  return (
    <div className="flex-grow flex flex-col items-center py-7 px-4 md:px-8">
      <div className="w-full max-w-[960px] flex flex-col gap-5">
        <MonthSwitcher
          label={MONTH_AND_YEAR.format(selected)}
          canGoForward={budgetStore.canGoForward}
          onPrevious={() => {
            void budgetStore.showPreviousMonth();
          }}
          onNext={() => {
            void budgetStore.showNextMonth();
          }}
        />

        {error && (
          <ErrorState layout="banner" title="The month could not be loaded" message={error} />
        )}

        <Card
          variant="surface"
          aria-busy={isLoading}
          className={`flex flex-col gap-2.5 px-6 py-7 md:px-8 transition-opacity ${isLoading ? "opacity-60" : ""}`}
        >
          <span className="text-md font-medium text-muted-foreground">{heading}</span>
          <p className="m-0 flex flex-wrap items-baseline gap-3">
            <span className="tabular-nums text-[46px] font-bold leading-none tracking-[-0.025em]">
              {AMOUNT.format(Number(summary.total))}
            </span>
            <span className="text-xl font-semibold text-muted-foreground">{currency}</span>
          </p>
          <span className="tabular-nums text-md text-muted-foreground">
            {summary.receipt_count === 1
              ? "1 receipt"
              : `${String(summary.receipt_count)} receipts`}
          </span>
        </Card>

        {summary.excluded_count > 0 && (
          <Note tone="warning">
            <span className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span className="tabular-nums">
                {summary.excluded_count === 1
                  ? "1 receipt"
                  : `${String(summary.excluded_count)} receipts`}{" "}
                worth {AMOUNT.format(Number(summary.excluded_amount))} {currency}{" "}
                {summary.excluded_count === 1 ? "is" : "are"} not in this total — the date or total
                could not be read.
              </span>
              <Link to="/receipts?status=manual_review" className="shrink-0 underline">
                {summary.excluded_count === 1 ? "Resolve it" : "Resolve them"}
              </Link>
            </span>
          </Note>
        )}
      </div>
    </div>
  );
});

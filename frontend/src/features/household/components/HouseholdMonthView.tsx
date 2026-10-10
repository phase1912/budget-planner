import { useEffect } from "react";
import { observer } from "mobx-react-lite";

import { Card, ErrorState, LoadingState, Meter, Note } from "@/shared/components";
import { LimitStatus } from "@/features/dashboard/components/LimitStatus";
import { useStores } from "@/stores/StoreContext";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * The household's month on the dashboard (F12.5, ADR-0017, BRD D1-D4, D7): what everyone
 * spent together, against the household budget, and who spent what — each member's
 * private receipts as one sum, never what they were.
 */
export const HouseholdMonthView = observer(function HouseholdMonthView({
  year,
  month,
  currency,
}: {
  year: number;
  month: number;
  currency: string;
}) {
  const { householdStore } = useStores();
  const summary = householdStore.month;
  const { error, isLoading } = householdStore.monthState;

  useEffect(() => {
    void householdStore.loadMonth(year, month);
  }, [householdStore, year, month]);

  if (!summary) {
    return error ? (
      <ErrorState
        layout="banner"
        title="The household's month could not be loaded"
        message={error}
      />
    ) : (
      <LoadingState title="Loading the household's month…" />
    );
  }

  const total = Number(summary.total);
  const wide = (text: string) => <span className="hidden md:inline">{text}</span>;
  const meta = (
    <span className="tabular-nums text-sm text-muted-foreground md:text-md">
      {summary.is_complete
        ? `${String(summary.days)} of ${String(summary.days)} days`
        : `${String(summary.days_elapsed)} of ${String(summary.days)} days`}{" "}
      · {summary.receipt_count === 1 ? "1 receipt" : `${String(summary.receipt_count)} receipts`}
    </span>
  );

  return (
    <>
      <Card
        variant="surface"
        aria-busy={isLoading}
        className={`flex flex-col gap-3 p-5 md:gap-2.5 md:px-8 md:py-7 transition-opacity ${isLoading ? "opacity-60" : ""}`}
      >
        <span className="text-base font-medium text-muted-foreground md:text-md">
          {summary.is_complete ? "Spent together" : "Spent together so far"}
          {wide(" this month")}
        </span>
        <p className="m-0 flex flex-wrap items-baseline gap-2 md:gap-3">
          <span className="tabular-nums text-[36px] font-bold leading-none tracking-[-0.025em] md:text-[46px]">
            {AMOUNT.format(total)}
          </span>
          <span className="text-[16px] font-semibold text-muted-foreground md:text-xl">
            {currency}
          </span>
        </p>
        {summary.limit ? (
          <LimitStatus
            limit={summary.limit.limit}
            percent={summary.limit.percent}
            remaining={summary.limit.remaining}
            currency={currency}
            whose="the household's"
          >
            {meta}
          </LimitStatus>
        ) : (
          meta
        )}
      </Card>

      {summary.excluded_count > 0 && (
        <Note tone="warning">
          {summary.excluded_count === 1
            ? "1 receipt"
            : `${String(summary.excluded_count)} receipts`}{" "}
          worth {AMOUNT.format(Number(summary.excluded_amount))} {currency}{" "}
          {summary.excluded_count === 1 ? "is" : "are"} under review and not in this total. Each
          member resolves their own.
        </Note>
      )}

      <Card variant="surface" className="flex flex-col gap-4 p-5 md:px-8 md:py-6">
        <h2 className="m-0 text-lg font-semibold">Who spent what</h2>
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {summary.members.map((member) => {
            const memberTotal = Number(member.total);
            const share = total > 0 ? Math.round((memberTotal / total) * 100) : 0;
            const privateTotal = Number(member.private_total);
            return (
              <li key={member.user_id} className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="min-w-0 truncate font-semibold">{member.first_name}</span>
                  <span className="shrink-0 tabular-nums font-semibold">
                    {AMOUNT.format(memberTotal)}
                    {wide(` ${currency}`)}
                    <span className="ml-2 text-md font-normal text-muted-foreground">{share}%</span>
                  </span>
                </div>
                <Meter value={share} />
                {privateTotal > 0 && (
                  <span className="tabular-nums text-sm text-muted-foreground">
                    of which private: {AMOUNT.format(privateTotal)} {currency}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </Card>
    </>
  );
});

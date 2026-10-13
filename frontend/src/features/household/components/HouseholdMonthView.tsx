import { useEffect } from "react";
import { observer } from "mobx-react-lite";

import { Card, ErrorState, LoadingState, Meter, Note } from "@/shared/components";
import { LimitStatus } from "@/features/dashboard/components/LimitStatus";
import { useStores } from "@/stores/StoreContext";
import { numberFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const AMOUNT = numberFormat({
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
  const { t } = useTranslation("dashboard");
  const summary = householdStore.month;
  const { error, isLoading } = householdStore.monthState;

  useEffect(() => {
    void householdStore.loadMonth(year, month);
  }, [householdStore, year, month]);

  if (!summary) {
    return error ? (
      <ErrorState layout="banner" title={t("household.loadFailed")} message={error} />
    ) : (
      <LoadingState title={t("household.loading")} />
    );
  }

  const total = Number(summary.total);
  const wide = (text: string) => <span className="hidden md:inline">{text}</span>;
  const meta = (
    <span className="tabular-nums text-sm text-muted-foreground md:text-md">
      {t("days", {
        elapsed: summary.is_complete ? summary.days : summary.days_elapsed,
        days: summary.days,
      })}{" "}
      · {t("receipts", { count: summary.receipt_count })}
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
          {summary.is_complete ? t("household.spentTogether") : t("household.spentTogetherSoFar")}
          {wide(t("household.thisMonth"))}
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
            household
          >
            {meta}
          </LimitStatus>
        ) : (
          meta
        )}
      </Card>

      {summary.excluded_count > 0 && (
        <Note tone="warning">
          {t("household.underReview", {
            count: summary.excluded_count,
            amount: AMOUNT.format(Number(summary.excluded_amount)),
            currency,
          })}
        </Note>
      )}

      <Card variant="surface" className="flex flex-col gap-4 p-5 md:px-8 md:py-6">
        <h2 className="m-0 text-lg font-semibold">{t("household.who")}</h2>
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
                    {t("household.private", { amount: AMOUNT.format(privateTotal), currency })}
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

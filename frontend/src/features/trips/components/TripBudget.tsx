import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { Meter } from "@/shared/components";
import type { TripDetail } from "@/stores/TripsStore";

/**
 * How much of a personal trip's budget is spent and what is left (F20.3). Past the
 * budget the bar reads in the error tone, is notched where the budget sat, and the text
 * says by how much; the share is never clamped at 100%.
 */
export function TripBudget({ trip, currency }: { trip: TripDetail; currency: string }) {
  const { t } = useTranslation("trips");
  if (trip.budget == null || trip.budget_left == null) return null;
  const budget = Number(trip.budget);
  const left = Number(trip.budget_left);
  const over = left < 0;
  const percent = Math.floor((Number(trip.total) / budget) * 100);
  const mark = over ? (budget / (budget - left)) * 100 : undefined;
  return (
    <div className="flex flex-col gap-1.75">
      <Meter value={over ? 100 : percent} tone={over ? "error" : "primary"} mark={mark} />
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 text-base md:text-md">
        <span className={`tabular-nums font-semibold ${over ? "text-error" : "text-primary"}`}>
          {t("budget.of", { percent, budget: formatAmount(budget), currency })}
        </span>
        <span
          className={`tabular-nums ${over ? "font-semibold text-error" : "text-muted-foreground"}`}
        >
          {t(over ? "budget.over" : "budget.left", {
            amount: formatAmount(Math.abs(left)),
            currency,
          })}
        </span>
      </div>
    </div>
  );
}

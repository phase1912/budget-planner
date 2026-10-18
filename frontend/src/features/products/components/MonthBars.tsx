import { useState } from "react";
import { useTranslation } from "react-i18next";

import { dateFormat, formatAmount } from "@/i18n/format";
import type { Exploration } from "@/stores/ExplorationStore";

const SHORT = dateFormat({ month: "short" });
const LONG = dateFormat({ month: "long", year: "numeric" });

/**
 * What the selection cost month by month (F16.2, explore.html): a column per month,
 * tapping one names its amount and how many times it was bought; opens on the latest.
 */
export function MonthBars({
  months,
  currency,
}: {
  months: Exploration["months"];
  currency: string;
}) {
  const { t } = useTranslation("products");
  const [chosen, setChosen] = useState<string | null>(null);
  const top = Math.max(...months.map((m) => Number(m.amounts.spent)), 0);
  const selected = months.find((m) => m.month === chosen) ?? months[months.length - 1];
  const day = (month: string) => new Date(`${month}T00:00:00`);
  const labelled = months.length <= 12;

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="m-0 text-lg font-extrabold">{t("explore.byMonth")}</h3>
        {selected && (
          <span className="text-md font-bold text-primary tabular-nums" aria-live="polite">
            {SHORT.format(day(selected.month))} · {formatAmount(selected.amounts.spent)} {currency}
          </span>
        )}
      </div>
      <div className="flex h-28 items-end gap-1">
        {months.map((month) => {
          const share = top > 0 ? Number(month.amounts.spent) / top : 0;
          const isSelected = month.month === selected?.month;
          return (
            <button
              key={month.month}
              type="button"
              aria-pressed={isSelected}
              aria-label={`${LONG.format(day(month.month))}: ${
                month.amounts.times > 0
                  ? `${formatAmount(month.amounts.spent)} ${currency}, ${t("explore.times", { count: month.amounts.times })}`
                  : t("explore.none")
              }`}
              onClick={() => {
                setChosen(month.month);
              }}
              className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"
            >
              <span
                className={`block w-full rounded-t-[5px] rounded-b-[2px] ${
                  isSelected ? "bg-primary" : "bg-tone-primary-bg"
                }`}
                style={{ height: `${String(Math.max(4, share * 100))}%` }}
              />
              {labelled && (
                <span className="text-xs text-muted-foreground">
                  {SHORT.format(day(month.month))}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}

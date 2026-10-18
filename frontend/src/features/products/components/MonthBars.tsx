import { useState } from "react";
import { useTranslation } from "react-i18next";

import { dateFormat, formatAmount } from "@/i18n/format";
import type { Exploration } from "@/stores/ExplorationStore";

const SHORT = dateFormat({ month: "short" });
const LONG = dateFormat({ month: "long", year: "numeric" });

/**
 * What the selection cost month by month (F16.2, explore.html): a column per month,
 * stacked by product in each product's colour; tapping one names its month and amount.
 * Opens on the latest month.
 */
export function MonthBars({
  months,
  currency,
  colourOf,
}: {
  months: Exploration["months"];
  currency: string;
  colourOf: (productId: string) => string;
}) {
  const { t } = useTranslation("products");
  const [chosen, setChosen] = useState<string | null>(null);
  const top = Math.max(...months.map((m) => Number(m.amounts.spent)), 0);
  const selected = months.find((m) => m.month === chosen) ?? months[months.length - 1];
  const day = (month: string) => new Date(`${month}T00:00:00`);
  const labelled = months.length <= 12;

  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="m-0 text-xl font-extrabold">{t("explore.byMonth")}</h2>
        {selected && (
          <span className="text-md font-bold text-primary tabular-nums" aria-live="polite">
            {SHORT.format(day(selected.month))} · {formatAmount(selected.amounts.spent)} {currency}
          </span>
        )}
      </div>
      <div className="flex h-40 items-end gap-1.5 md:gap-2.5">
        {months.map((month) => {
          const isSelected = month.month === selected?.month;
          const total = Number(month.amounts.spent);
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
              className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5"
            >
              <span
                className={`flex w-full flex-col-reverse gap-0.5 transition-opacity ${isSelected ? "" : "opacity-60"}`}
                style={{ height: `${String(top > 0 ? Math.max(3, (total / top) * 100) : 3)}%` }}
              >
                {total === 0 ? (
                  <span className="block h-full w-full rounded-[4px] bg-muted" />
                ) : (
                  month.by_product.map((part) => (
                    <span
                      key={part.product_id}
                      className="block w-full rounded-[5px]"
                      style={{
                        height: `${String((Number(part.spent) / total) * 100)}%`,
                        background: colourOf(part.product_id),
                      }}
                    />
                  ))
                )}
              </span>
              {labelled && (
                <span className="text-sm text-muted-foreground">
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

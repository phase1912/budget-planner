import { useState } from "react";
import { useTranslation } from "react-i18next";

import { dateFormat, numberFormat } from "@/i18n/format";
import type { DailySpend } from "@/stores/StatisticsStore";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "short" });
const LONG_DAY = dateFormat({ day: "numeric", month: "long" });

interface DailyBarsProps {
  daily: DailySpend;
  currency: string;
  today: string;
}

const asDate = (day: string) => new Date(`${day}T00:00:00`);

/**
 * Spending day by day (F23.4, docs/design/screens/v2/spending.html): one bar per day,
 * scaled to the period's biggest; tapping a bar names its day and amount. Opens on the
 * latest day something was bought, and gives the period's daily average beneath.
 */
export function DailyBars({ daily, currency, today }: DailyBarsProps) {
  const { t } = useTranslation("statistics");
  const passed = daily.days.filter((d) => d.day <= today);
  const [chosen, setChosen] = useState<string | null>(null);
  const lastSpent = passed.filter((d) => Number(d.total) > 0).pop();
  const selected =
    daily.days.find((d) => d.day === chosen) ??
    lastSpent ??
    passed[passed.length - 1] ??
    daily.days[0];
  const peak = Math.max(...daily.days.map((d) => Number(d.total)), 0);

  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-4 md:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="m-0 text-xl font-extrabold">{t("byDay.title")}</h2>
        {selected && (
          <span className="text-md font-bold text-primary tabular-nums" aria-live="polite">
            {DAY.format(asDate(selected.day))} · {WHOLE.format(Number(selected.total))} {currency}
          </span>
        )}
      </div>
      <div className="flex h-30 items-end gap-0.5 md:gap-1">
        {daily.days.map((d) => {
          const share = peak > 0 ? Number(d.total) / peak : 0;
          const isSelected = d.day === selected?.day;
          return (
            <button
              key={d.day}
              type="button"
              aria-pressed={isSelected}
              aria-label={t("byDay.bar", {
                date: LONG_DAY.format(asDate(d.day)),
                amount: WHOLE.format(Number(d.total)),
                currency,
              })}
              onClick={() => {
                setChosen(d.day);
              }}
              className="flex h-full min-w-0 flex-1 items-end"
            >
              <span
                className={`block w-full rounded-t-[5px] rounded-b-[2px] ${
                  isSelected ? "bg-primary" : "bg-tone-primary-bg"
                }`}
                style={{ height: `${String(Math.max(4, share * 100))}%` }}
              />
            </button>
          );
        })}
      </div>
      <p className="m-0 text-md text-muted-foreground tabular-nums">
        {t("byDay.average", { amount: WHOLE.format(Number(daily.average)), currency })}
      </p>
    </section>
  );
}

import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { dateFormat, numberFormat } from "@/i18n/format";
import type { DailySpend } from "@/stores/StatisticsStore";
import { useStores } from "@/stores/StoreContext";
import { asDate, type Day } from "../chartDay";
import { Calendar, ChartViewSwitch, Column, DayRows } from "./DayChartViews";
import { ReceiptRows } from "./SpendingSections";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "short" });
const LONG_DAY = dateFormat({ day: "numeric", month: "long" });

interface DailyBarsProps {
  daily: DailySpend;
  currency: string;
  today: string;
}

/**
 * Spending day by day (F23.4, docs/design/screens/v2/spending.html), drawn as columns, a
 * row a day or a calendar, as the user last chose (F23.22.2). Tapping a day names its sum
 * and lists its receipts beneath (F23.22.1). Opens on the latest day something was bought,
 * and gives the period's daily average beneath.
 */
export const DailyBars = observer(function DailyBars({ daily, currency, today }: DailyBarsProps) {
  const { statisticsStore } = useStores();
  const { t } = useTranslation("statistics");
  const [chosen, setChosen] = useState<string | null>(null);
  const passed = daily.days.filter((d) => d.day <= today);
  const lastSpent = passed.filter((d) => Number(d.total) > 0).pop();
  const selected =
    daily.days.find((d) => d.day === chosen) ??
    lastSpent ??
    passed[passed.length - 1] ??
    daily.days[0];
  const peak = Math.max(...daily.days.map((d) => Number(d.total)), 0);
  const view = statisticsStore.chartView;
  const tapped = statisticsStore.day;

  const choose = (day: string) => {
    setChosen(day);
    void statisticsStore.openDay(day);
  };
  const dayProps = (d: Day) => ({
    day: d,
    share: peak > 0 ? Number(d.total) / peak : 0,
    isSelected: d.day === selected?.day,
    label: t("byDay.bar", {
      date: LONG_DAY.format(asDate(d.day)),
      amount: WHOLE.format(Number(d.total)),
      currency,
    }),
    onChoose: choose,
  });

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
      <ChartViewSwitch />
      {view === "columns" && (
        <div className="flex h-30 items-end gap-0.5 md:gap-1">
          {daily.days.map((d) => (
            <Column key={d.day} {...dayProps(d)} />
          ))}
        </div>
      )}
      {view === "days" && <DayRows days={passed} currency={currency} dayProps={dayProps} />}
      {view === "calendar" && <Calendar days={daily.days} dayProps={dayProps} />}
      <p className="m-0 text-md text-muted-foreground tabular-nums">
        {t("byDay.average", { amount: WHOLE.format(Number(daily.average)), currency })}
      </p>
      {tapped && (
        <div className="flex flex-col gap-2" aria-live="polite">
          <h3 className="m-0 text-lg font-bold">
            {t("byDay.receiptsOf", { date: LONG_DAY.format(asDate(tapped)) })}
          </h3>
          {statisticsStore.isLoadingDay && statisticsStore.dayReceipts.length === 0 ? (
            <p className="m-0 text-md text-muted-foreground">{t("sections.loading")}</p>
          ) : statisticsStore.dayReceipts.length === 0 ? (
            <p className="m-0 text-md text-muted-foreground">{t("byDay.noReceipts")}</p>
          ) : (
            <ReceiptRows receipts={statisticsStore.dayReceipts} />
          )}
        </div>
      )}
    </section>
  );
});

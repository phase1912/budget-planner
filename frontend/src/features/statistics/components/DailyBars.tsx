import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { dateFormat, numberFormat } from "@/i18n/format";
import { SegmentedControl } from "@/shared/components";
import type { ChartView, DailySpend } from "@/stores/StatisticsStore";
import { useStores } from "@/stores/StoreContext";
import { ReceiptRows } from "./SpendingSections";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "short" });
const LONG_DAY = dateFormat({ day: "numeric", month: "long" });
const WEEKDAY = dateFormat({ weekday: "narrow" });
const VIEWS: ChartView[] = ["columns", "days", "calendar"];

type Day = DailySpend["days"][number];

interface DailyBarsProps {
  daily: DailySpend;
  currency: string;
  today: string;
}

const asDate = (day: string) => new Date(`${day}T00:00:00`);

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
      <SegmentedControl
        label={t("byDay.view")}
        size="sm"
        fill
        value={view}
        onChange={(next) => {
          statisticsStore.setChartView(next);
        }}
        options={VIEWS.map((v) => ({ value: v, label: t(`byDay.views.${v}`) }))}
      />
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

interface DayProps {
  day: Day;
  share: number;
  isSelected: boolean;
  label: string;
  onChoose: (day: string) => void;
}

function Column({ day, share, isSelected, label, onChoose }: DayProps) {
  return (
    <button
      type="button"
      aria-pressed={isSelected}
      aria-label={label}
      onClick={() => {
        onChoose(day.day);
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
}

/** A row for each day something was bought, newest last, the bar running across. */
function DayRows({
  days,
  currency,
  dayProps,
}: {
  days: Day[];
  currency: string;
  dayProps: (d: Day) => DayProps;
}) {
  const { t } = useTranslation("statistics");
  const spent = days.filter((d) => Number(d.total) > 0);
  if (spent.length === 0) {
    return <p className="m-0 text-md text-muted-foreground">{t("byDay.nothingYet")}</p>;
  }
  return (
    <ul className="m-0 flex list-none flex-col p-0">
      {spent.map((d) => {
        const { share, isSelected, label, onChoose } = dayProps(d);
        return (
          <li key={d.day}>
            <button
              type="button"
              aria-pressed={isSelected}
              aria-label={label}
              onClick={() => {
                onChoose(d.day);
              }}
              className="flex min-h-11 w-full items-center gap-3 text-left"
            >
              <span
                className={`w-14 shrink-0 text-md tabular-nums ${isSelected ? "font-bold text-primary" : "text-muted-foreground"}`}
              >
                {DAY.format(asDate(d.day))}
              </span>
              <span className="flex h-3 min-w-0 flex-1 overflow-hidden rounded-pill bg-muted">
                <span
                  className={`block h-full rounded-pill ${isSelected ? "bg-primary" : "bg-tone-primary-text"}`}
                  style={{ width: `${String(Math.max(2, share * 100))}%` }}
                />
              </span>
              <span className="w-20 shrink-0 text-right text-md font-bold tabular-nums">
                {WHOLE.format(Number(d.total))} {currency}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** The period as weeks, Monday first, each day shaded by its share of the biggest. */
function Calendar({ days, dayProps }: { days: Day[]; dayProps: (d: Day) => DayProps }) {
  const first = days[0];
  if (!first) return null;
  // Monday is 0: the blanks before the period's first day line it up under its weekday.
  const lead = (asDate(first.day).getDay() + 6) % 7;
  // 1 January 2024 was a Monday.
  const weekdays = Array.from({ length: 7 }, (_, i) => WEEKDAY.format(new Date(2024, 0, 1 + i)));
  return (
    <div className="grid grid-cols-7 gap-1">
      {weekdays.map((w, i) => (
        <span key={i} aria-hidden="true" className="text-center text-sm text-muted-foreground">
          {w}
        </span>
      ))}
      {Array.from({ length: lead }, (_, i) => (
        <span key={`blank-${String(i)}`} aria-hidden="true" />
      ))}
      {days.map((d) => {
        const { share, isSelected, label, onChoose } = dayProps(d);
        const strong = share > 0.5;
        return (
          <button
            key={d.day}
            type="button"
            aria-pressed={isSelected}
            aria-label={label}
            onClick={() => {
              onChoose(d.day);
            }}
            className={`relative flex min-h-11 items-center justify-center overflow-hidden rounded-control bg-muted text-md tabular-nums ${
              isSelected ? "ring-2 ring-primary" : ""
            }`}
          >
            {share > 0 && (
              <span
                aria-hidden="true"
                className="absolute inset-0 bg-primary"
                style={{ opacity: 0.2 + share * 0.8 }}
              />
            )}
            <span
              className={`relative font-semibold ${strong ? "text-primary-foreground" : "text-foreground"}`}
            >
              {asDate(d.day).getDate()}
            </span>
          </button>
        );
      })}
    </div>
  );
}

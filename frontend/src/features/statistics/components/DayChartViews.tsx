import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { dateFormat, numberFormat } from "@/i18n/format";
import { SegmentedControl } from "@/shared/components";
import type { ChartView } from "@/stores/StatisticsStore";
import { useStores } from "@/stores/StoreContext";
import { asDate, type Day } from "../chartDay";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "short" });
const WEEKDAY = dateFormat({ weekday: "narrow" });
const VIEWS: ChartView[] = ["columns", "days", "calendar"];

/**
 * How a day-by-day chart is drawn — columns, a row a day or a calendar (F23.22.2) — one
 * choice for the personal and the family chart alike, kept in this browser.
 */
export const ChartViewSwitch = observer(function ChartViewSwitch() {
  const { statisticsStore } = useStores();
  const { t } = useTranslation("statistics");
  return (
    <SegmentedControl
      label={t("byDay.view")}
      size="sm"
      fill
      value={statisticsStore.chartView}
      onChange={(next) => {
        statisticsStore.setChartView(next);
      }}
      options={VIEWS.map((v) => ({ value: v, label: t(`byDay.views.${v}`) }))}
    />
  );
});

/** One day as a view draws it: its share of the biggest, and what tapping it does. */
export interface DayProps {
  day: Day;
  share: number;
  isSelected: boolean;
  label: string;
  onChoose: (day: string) => void;
}

/** A column of the columns view. */
export function Column({ day, share, isSelected, label, onChoose }: DayProps) {
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
export function DayRows({
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
                className={`w-16 shrink-0 whitespace-nowrap text-md tabular-nums ${isSelected ? "font-bold text-primary" : "text-muted-foreground"}`}
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
export function Calendar({ days, dayProps }: { days: Day[]; dayProps: (d: Day) => DayProps }) {
  const first = days[0];
  if (!first) return null;
  // Monday is 0: the blanks before the period's first day line it up under its weekday.
  const lead = (asDate(first.day).getDay() + 6) % 7;
  // 1 January 2024 was a Monday.
  const weekdays = Array.from({ length: 7 }, (_, i) => WEEKDAY.format(new Date(2024, 0, 1 + i)));
  return (
    <div className="grid w-full grid-cols-7 gap-1 md:max-w-xl">
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

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { numberFormat } from "@/i18n/format";
import type { TripDetail } from "@/stores/TripsStore";
import { formatTripDay, formatTripDayShort } from "../tripFormat";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });

/**
 * What each day of a trip cost (F20.3, holiday.html): a column a day, a quiet day low and
 * faint; tapping one names its day and amount. Opens on the dearest day.
 */
export function TripDays({ trip, currency }: { trip: TripDetail; currency: string }) {
  const { t } = useTranslation("trips");
  const days = trip.days;
  const top = Math.max(...days.map((d) => Number(d.total)), 0);
  const dearest = days.reduce<(typeof days)[number] | undefined>(
    (best, d) => (!best || Number(d.total) > Number(best.total) ? d : best),
    undefined,
  );
  const [chosen, setChosen] = useState<string | null>(null);
  const selected = days.find((d) => d.day === chosen) ?? dearest;
  if (days.length === 0) return null;

  return (
    <section className="flex flex-col gap-3 rounded-card bg-surface p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="m-0 text-xl font-extrabold">{t("story.days")}</h2>
        {selected && (
          <span className="text-md font-bold text-primary tabular-nums" aria-live="polite">
            {formatTripDayShort(selected.day)} · {WHOLE.format(Number(selected.total))} {currency}
          </span>
        )}
      </div>
      <div className="flex h-32 items-end gap-1">
        {days.map((d) => {
          const value = Number(d.total);
          const isSelected = d.day === selected?.day;
          return (
            <button
              key={d.day}
              type="button"
              aria-pressed={isSelected}
              aria-label={`${formatTripDay(d.day)}, ${WHOLE.format(value)} ${currency}`}
              onClick={() => {
                setChosen(d.day);
              }}
              className="flex h-full min-w-0 flex-1 items-end"
            >
              <span
                className={`block w-full rounded-t-[5px] rounded-b-[2px] ${
                  value === 0 ? "bg-muted" : isSelected ? "bg-primary" : "bg-[var(--cat-transport)]"
                }`}
                style={{ height: `${String(top > 0 ? Math.max(5, (value / top) * 100) : 5)}%` }}
              />
            </button>
          );
        })}
      </div>
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>{formatTripDayShort(days[0]?.day ?? trip.start_date)}</span>
        <span>{formatTripDayShort(days[days.length - 1]?.day ?? trip.end_date)}</span>
      </div>
    </section>
  );
}

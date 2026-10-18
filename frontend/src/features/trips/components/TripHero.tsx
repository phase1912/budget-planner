import { ChevronLeft, Pencil, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { numberFormat } from "@/i18n/format";
import type { TripDetail } from "@/stores/TripsStore";
import { isoDay } from "@/stores/StatisticsStore";
import { formatTripSpan } from "../tripFormat";
import { tripMoment } from "../tripDays";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
// Controls on the primary fill: the foreground colour, faint.
const ON_FILL = "bg-[color-mix(in_srgb,var(--color-primary-foreground)_18%,transparent)]";

/**
 * A trip's head (holiday.html): the way back, where today falls in it, its kind, dates
 * and name, and for a holiday what it cost against its budget with what is left a day.
 * A business trip shows what the employer owes back instead.
 */
export function TripHero({
  trip,
  currency,
  place,
  onEdit,
  onDelete,
}: {
  trip: TripDetail;
  currency: string;
  place: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation("trips");
  const moment = tripMoment(trip.start_date, trip.end_date, isoDay(new Date()));
  const spent = Number(trip.total);
  const budget = trip.budget == null ? null : Number(trip.budget);
  const left = budget === null ? null : budget - spent;
  const holiday = trip.kind === "personal";

  return (
    <header className="flex flex-col gap-3 rounded-hero bg-primary p-5 text-primary-foreground">
      <div className="flex items-center justify-between gap-2">
        <Link
          to={holiday ? "/plan" : "/trips?kind=business"}
          aria-label={t("detail.back")}
          className={`flex h-11 w-11 items-center justify-center rounded-pill ${ON_FILL}`}
        >
          <ChevronLeft size={20} aria-hidden="true" />
        </Link>
        <span className="flex items-center gap-2">
          <span className={`rounded-pill px-3 py-1.5 text-md font-bold ${ON_FILL}`}>
            {moment.kind === "during"
              ? t("hero.day", { day: moment.day, of: moment.of })
              : moment.kind === "before"
                ? t("hero.inDays", { count: moment.inDays })
                : t("hero.over")}
          </span>
          <button
            type="button"
            aria-label={t("detail.edit")}
            onClick={onEdit}
            className={`flex h-11 w-11 items-center justify-center rounded-pill ${ON_FILL}`}
          >
            <Pencil size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            aria-label={t("detail.delete")}
            onClick={onDelete}
            className={`flex h-11 w-11 items-center justify-center rounded-pill ${ON_FILL}`}
          >
            <Trash2 size={16} aria-hidden="true" />
          </button>
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-md font-bold opacity-90">
          {holiday ? t("hero.holiday") : t(`kind.${trip.kind}`)} ·{" "}
          {formatTripSpan(trip.start_date, trip.end_date, new Date().getFullYear())}
          {place && ` · ${place}`}
        </span>
        <h1 className="m-0 break-words text-3xl font-extrabold tracking-[-0.02em]">{trip.name}</h1>
        {trip.purpose && <p className="m-0 text-md opacity-90">{trip.purpose}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3 text-lg font-extrabold tabular-nums">
          <span>
            {holiday
              ? t("hero.spent", { amount: WHOLE.format(spent), currency })
              : t("hero.toReimburse", { amount: WHOLE.format(spent), currency })}
          </span>
          {budget !== null && (
            <span>{t("hero.of", { amount: WHOLE.format(budget), currency })}</span>
          )}
        </div>
        {budget !== null && budget > 0 && (
          <span className={`h-2.5 overflow-hidden rounded-pill ${ON_FILL}`} aria-hidden="true">
            <span
              className={`block h-2.5 rounded-pill ${spent > budget ? "bg-error" : "bg-primary-foreground"}`}
              style={{ width: `${String(Math.min(100, (spent / budget) * 100))}%` }}
            />
          </span>
        )}
        <span className="text-md font-semibold opacity-90 tabular-nums">
          {left !== null && left < 0
            ? t("hero.overBy", { amount: WHOLE.format(-left), currency })
            : left !== null && moment.kind === "during"
              ? t("hero.perDay", {
                  amount: WHOLE.format(left / moment.left),
                  currency,
                  count: moment.left,
                })
              : t("receipts", { count: trip.receipt_count })}
        </span>
      </div>
    </header>
  );
}

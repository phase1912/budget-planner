import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { Pill } from "@/shared/components";
import type { Trip } from "@/stores/TripsStore";
import { countryName, formatTripDay } from "../tripFormat";

/** One trip in the list: where and when, how many receipts, and what it cost (F20.1). */
export function TripCard({ trip, currency }: { trip: Trip; currency: string }) {
  const { t } = useTranslation("trips");
  const place = [trip.city, trip.country ? countryName(trip.country) : null]
    .filter(Boolean)
    .join(", ");
  return (
    <Link
      to={`/trips/${trip.id}`}
      className="flex flex-col gap-2 rounded-card border border-border bg-background p-4 no-underline text-foreground transition-colors hover:bg-surface-hover md:flex-row md:items-center md:justify-between md:gap-4"
    >
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-lg font-bold">{trip.name}</span>
          <Pill size="sm" tone={trip.kind === "business" ? "info" : "accent"}>
            {t(`kind.${trip.kind}`)}
          </Pill>
        </div>
        <span className="text-base text-muted-foreground">
          {t("dates", { start: formatTripDay(trip.start_date), end: formatTripDay(trip.end_date) })}
          {place && ` · ${place}`}
        </span>
      </div>
      <div className="flex items-baseline justify-between gap-3 md:flex-col md:items-end md:gap-0.5">
        <span className="text-base text-muted-foreground">
          {t("receipts", { count: trip.receipt_count })}
        </span>
        <span className="text-lg font-bold tabular-nums">
          {formatAmount(trip.total)} {currency}
        </span>
      </div>
    </Link>
  );
}

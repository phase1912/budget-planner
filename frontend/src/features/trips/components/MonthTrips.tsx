import { Plane } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import type { Trip } from "@/stores/TripsStore";

/**
 * The month's trips under its total (F20.1). A personal trip's spending is part of the
 * total and shown as "of which"; a business trip's is not, and is shown as what the
 * employer owes back.
 */
export function MonthTrips({ trips, currency }: { trips: Trip[]; currency: string }) {
  const { t } = useTranslation("trips");
  if (trips.length === 0) return null;
  return (
    <ul className="m-0 flex list-none flex-col gap-1 p-0">
      {trips.map((trip) => (
        <li key={trip.id}>
          <Link
            to={`/trips/${trip.id}`}
            aria-label={`${t("dashboard.open")}: ${trip.name}`}
            className="inline-flex min-h-11 items-center gap-2 text-base text-muted-foreground no-underline hover:text-foreground md:min-h-0 md:text-md"
          >
            <Plane size={14} aria-hidden="true" className="shrink-0" />
            <span className="tabular-nums">
              {t(`dashboard.${trip.kind}`, {
                name: trip.name,
                amount: formatAmount(trip.total),
                currency,
              })}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

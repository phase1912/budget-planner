import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { categoryName } from "@/shared/categoryName";
import { Card, Meter } from "@/shared/components";
import type { TripDetail } from "@/stores/TripsStore";
import { formatTripDay } from "../tripFormat";

/**
 * A trip read as one story (F20.3): what each of its days cost, a quiet day at zero, and
 * where the money went by category, each beside a bar against the largest. Side by side
 * from a laptop, one under the other on a phone or tablet.
 */
export function TripStory({ trip, currency }: { trip: TripDetail; currency: string }) {
  const { t } = useTranslation("trips");
  const topDay = Math.max(...trip.days.map((d) => Number(d.total)), 0);
  const topCategory = Math.max(...trip.categories.map((c) => Number(c.total)), 0);
  const share = (value: string, top: number) => (top > 0 ? (Number(value) / top) * 100 : 0);
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card className="flex flex-col gap-3 p-4 md:p-5">
        <h2 className="m-0 text-md font-semibold text-muted-foreground">{t("story.days")}</h2>
        <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
          {trip.days.map(({ day, total }) => (
            <li key={day} className="flex flex-col gap-1">
              <span className="flex items-baseline justify-between gap-3 text-md">
                <span>{formatTripDay(day)}</span>
                <span
                  className={`tabular-nums font-semibold ${Number(total) === 0 ? "text-muted-foreground" : ""}`}
                >
                  {formatAmount(total)} {currency}
                </span>
              </span>
              <Meter value={share(total, topDay)} />
            </li>
          ))}
        </ul>
      </Card>
      {trip.categories.length > 0 && (
        <Card className="flex flex-col gap-3 p-4 md:p-5">
          <h2 className="m-0 text-md font-semibold text-muted-foreground">
            {t("story.categories")}
          </h2>
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {trip.categories.map(({ category, total }) => (
              <li key={category} className="flex flex-col gap-1">
                <span className="flex items-baseline justify-between gap-3 text-md">
                  <span className="min-w-0 truncate">{categoryName(category)}</span>
                  <span className="shrink-0 tabular-nums font-semibold">
                    {formatAmount(total)} {currency}
                  </span>
                </span>
                <Meter value={share(total, topCategory)} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

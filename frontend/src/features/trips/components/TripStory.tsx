import { formatAmount } from "@/i18n/format";
import { categoryName } from "@/shared/categoryName";
import { CategoryIcon, Meter } from "@/shared/components";
import type { TripDetail } from "@/stores/TripsStore";

/**
 * Where a trip's money went by category (F20.3), each beside a bar against the largest;
 * the days have their own columns (TripDays).
 */
export function TripStory({ trip, currency }: { trip: TripDetail; currency: string }) {
  const top = Math.max(...trip.categories.map((c) => Number(c.total)), 0);
  const share = (value: string) => (top > 0 ? (Number(value) / top) * 100 : 0);
  return (
    <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
      {trip.categories.map(({ category, total }) => (
        <li key={category} className="flex flex-col gap-1">
          <span className="flex items-baseline justify-between gap-3 text-md">
            <span className="flex min-w-0 items-center gap-2">
              <CategoryIcon name={category} />
              <span className="truncate">{categoryName(category)}</span>
            </span>
            <span className="shrink-0 tabular-nums font-semibold">
              {formatAmount(total)} {currency}
            </span>
          </span>
          <Meter value={share(total)} />
        </li>
      ))}
    </ul>
  );
}

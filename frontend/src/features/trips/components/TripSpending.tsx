import { BedDouble, Bus, Package, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { Card } from "@/shared/components";
import type { ExpenseKind, TripDetail } from "@/stores/TripsStore";

const ICONS: Record<ExpenseKind, LucideIcon> = {
  transport: Bus,
  accommodation: BedDouble,
  meals: UtensilsCrossed,
  other: Package,
};

/**
 * What a trip cost by kind, in the account's currency, and what was paid in each
 * currency as printed (F20.2). Every kind is listed, a zero one too: "accommodation
 * 0.00" says the hotel was paid some other way.
 */
export function TripSpending({ trip, currency }: { trip: TripDetail; currency: string }) {
  const { t } = useTranslation("trips");
  const foreign = trip.by_currency.some((paid) => paid.currency !== currency);
  return (
    <Card className="flex flex-col gap-3 p-4 md:p-5">
      <h2 className="m-0 text-md font-semibold text-muted-foreground">{t("spending.title")}</h2>
      <ul className="m-0 grid list-none grid-cols-1 gap-2 p-0 md:grid-cols-2">
        {trip.by_kind.map(({ kind, total }) => {
          const Icon = ICONS[kind];
          return (
            <li
              key={kind}
              className="flex items-center justify-between gap-3 rounded-control bg-muted px-3 py-2.5"
            >
              <span className="flex items-center gap-2 text-md">
                <Icon size={16} aria-hidden="true" className="shrink-0 text-muted-foreground" />
                {t(`spending.${kind}`)}
              </span>
              <span
                className={`text-md font-semibold tabular-nums ${Number(total) === 0 ? "text-muted-foreground" : ""}`}
              >
                {formatAmount(total)} {currency}
              </span>
            </li>
          );
        })}
      </ul>
      {foreign && (
        <p className="m-0 flex flex-wrap gap-x-3 gap-y-1 text-base text-muted-foreground">
          <span>{t("spending.paidIn")}:</span>
          {trip.by_currency.map((paid) => (
            <span key={paid.currency} className="font-semibold tabular-nums text-foreground">
              {formatAmount(paid.total)} {paid.currency}
            </span>
          ))}
        </p>
      )}
    </Card>
  );
}

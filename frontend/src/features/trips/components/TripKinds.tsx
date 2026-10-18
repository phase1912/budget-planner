import { useTranslation } from "react-i18next";

import { numberFormat } from "@/i18n/format";
import type { TripDetail } from "@/stores/TripsStore";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const ORDER = ["accommodation", "meals", "transport", "other"] as const;
const DOT: Record<(typeof ORDER)[number], string> = {
  accommodation: "var(--color-primary)",
  meals: "var(--cat-transport)",
  transport: "var(--cat-dining)",
  other: "var(--cat-health)",
};

/**
 * What a trip cost by kind (F20.2, holiday.html): stays, food, getting around and the
 * rest as tiles, food also per day; and, when something was paid in another currency, what
 * was paid in each and that it was converted at the NBP rate of its day.
 */
export function TripKinds({ trip, currency }: { trip: TripDetail; currency: string }) {
  const { t } = useTranslation("trips");
  const totals = new Map(trip.by_kind.map((k) => [k.kind, Number(k.total)]));
  const days = Math.max(1, trip.days.length);
  const foreign = trip.by_currency.filter((paid) => paid.currency !== currency);

  return (
    <>
      <ul className="m-0 grid list-none grid-cols-2 gap-2.5 p-0 md:grid-cols-4">
        {ORDER.map((kind) => {
          const total = totals.get(kind) ?? 0;
          return (
            <li key={kind} className="flex flex-col gap-1 rounded-card bg-surface p-3.5">
              <span className="flex items-center gap-2 text-md font-bold text-muted-foreground">
                <span
                  className="h-2.5 w-2.5 rounded-pill"
                  style={{ background: DOT[kind] }}
                  aria-hidden="true"
                />
                {t(`spending.${kind}`)}
              </span>
              <span className="text-2xl font-extrabold tabular-nums">
                {WHOLE.format(total)} {currency}
              </span>
              {kind === "meals" && total > 0 && (
                <span className="text-sm text-muted-foreground tabular-nums">
                  {t("kinds.perDay", { amount: WHOLE.format(total / days), currency })}
                </span>
              )}
            </li>
          );
        })}
      </ul>
      {foreign.length > 0 && (
        <p className="m-0 flex gap-3 rounded-card bg-tone-primary-bg p-4 text-md">
          <span className="font-extrabold" aria-hidden="true">
            {foreign[0]?.currency === "EUR" ? "€" : "¤"}
          </span>
          <span>
            {t("kinds.converted", {
              paid: foreign.map((p) => `${WHOLE.format(Number(p.total))} ${p.currency}`).join(", "),
            })}
          </span>
        </p>
      )}
    </>
  );
}

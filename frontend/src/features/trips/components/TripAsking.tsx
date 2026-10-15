import { Briefcase } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { formatPurchase } from "@/shared/purchaseDate";
import { Button, Card } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { TripDetail } from "@/stores/TripsStore";

/**
 * A business trip's question about the receipts dated within it that arrived without
 * the wizard, by email or before the trip was recorded (F20.1). Each is the employer's
 * or the user's own; until answered it counts in the user's budget.
 */
export const TripAsking = observer(function TripAsking({ trip }: { trip: TripDetail }) {
  const { tripsStore } = useStores();
  const { t } = useTranslation(["trips", "receipts"]);
  if (trip.asking.length === 0) return null;
  return (
    <section
      aria-labelledby="trip-asking"
      className="flex flex-col gap-2.5 rounded-card border border-tone-warning-border bg-tone-warning-bg p-4 md:p-5"
    >
      <div className="flex flex-col gap-0.5">
        <h2 id="trip-asking" className="m-0 flex items-center gap-2 text-lg font-bold">
          <Briefcase size={18} aria-hidden="true" className="shrink-0" />
          {t("asking.title")}
        </h2>
        <p className="m-0 text-base text-tone-warning-prose">{t("asking.text")}</p>
      </div>
      <Card flush>
        <ul className="m-0 list-none p-0">
          {trip.asking.map((receipt) => {
            const merchant = receipt.merchant_name ?? t("receipts:list.unknownMerchant");
            return (
              <li
                key={receipt.id}
                className="flex flex-col gap-2.5 border-b border-border px-4 py-3 last:border-b-0 md:flex-row md:items-center md:justify-between"
              >
                <span className="flex min-w-0 items-baseline justify-between gap-3 md:justify-start">
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate text-md font-semibold">{merchant}</span>
                    <span className="text-base text-muted-foreground">
                      {formatPurchase(receipt.transaction_date ?? receipt.created_at, {
                        day: "numeric",
                        month: "short",
                      })}
                    </span>
                  </span>
                  <span className="shrink-0 text-md font-semibold tabular-nums md:ml-4">
                    {receipt.total_amount ? formatAmount(receipt.total_amount) : "—"}
                  </span>
                </span>
                <span
                  role="group"
                  aria-label={t("question.business", { name: trip.name })}
                  className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none"
                >
                  <Button
                    size="sm"
                    className="min-h-11 md:min-h-0"
                    onClick={() => void tripsStore.placeReceipt(receipt.id, trip.id)}
                  >
                    {t("question.yes")}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="min-h-11 md:min-h-0"
                    onClick={() => void tripsStore.placeReceipt(receipt.id, null)}
                  >
                    {t("question.no")}
                  </Button>
                </span>
              </li>
            );
          })}
        </ul>
      </Card>
    </section>
  );
});

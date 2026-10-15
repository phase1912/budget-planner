import { FileDown } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { Button, Card } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";
import type { TripDetail } from "@/stores/TripsStore";

/**
 * What the employer owes back for a business trip (F20.5): expenses, the per diem, the
 * advance taken off, and the sum to reimburse — or to return, when the advance was more —
 * with the settlement to hand in as a PDF carrying every receipt's photo, or as CSV.
 */
export const SettlementCard = observer(function SettlementCard({ trip }: { trip: TripDetail }) {
  const { exportStore } = useStores();
  const { t } = useTranslation("trips");
  const sums = trip.settlement;
  if (!sums) return null;
  const owed = sums.to_reimburse == null ? null : Number(sums.to_reimburse);
  const money = (amount: string) => `${formatAmount(amount)} ${sums.currency}`;
  const download = (format: "pdf" | "csv") => {
    void exportStore.start({ kind: "trip", format, trip_id: trip.id, compare: false });
  };

  return (
    <Card className="flex flex-col gap-3 p-4 md:p-5">
      <h2 className="m-0 text-lg font-bold">{t("settlement.title")}</h2>
      <dl className="m-0 flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between gap-3 text-md">
          <dt>{t("settlement.expenses")}</dt>
          <dd className="m-0 tabular-nums">{money(sums.expenses)}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3 text-md">
          <dt>{t("settlement.perDiem")}</dt>
          <dd className="m-0 tabular-nums">
            {sums.per_diem == null
              ? trip.per_diem
                ? t("settlement.pending")
                : t("settlement.perDiemNone")
              : `+ ${money(sums.per_diem)}`}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3 text-md">
          <dt>{t("settlement.advance")}</dt>
          <dd className="m-0 tabular-nums">− {money(sums.advance)}</dd>
        </div>
        <div className="flex items-baseline justify-between gap-3 border-t border-border pt-2 text-lg font-bold">
          <dt>
            {owed != null && owed < 0 ? t("settlement.toReturn") : t("settlement.toReimburse")}
          </dt>
          <dd className={`m-0 tabular-nums ${owed != null && owed < 0 ? "text-error" : ""}`}>
            {owed == null ? "—" : money(String(Math.abs(owed)))}
          </dd>
        </div>
      </dl>
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-end">
        <Button
          className="w-full md:w-auto"
          disabled={exportStore.busy.trip}
          onClick={() => {
            download("pdf");
          }}
        >
          <FileDown size={16} aria-hidden="true" />
          {t("settlement.download")} · {t("settlement.pdf")}
        </Button>
        <Button
          variant="secondary"
          className="w-full md:w-auto"
          disabled={exportStore.busy.trip}
          onClick={() => {
            download("csv");
          }}
        >
          {t("settlement.download")} · {t("settlement.csv")}
        </Button>
      </div>
    </Card>
  );
});

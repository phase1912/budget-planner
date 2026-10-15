import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import type { components } from "@/api/schema";
import { Button, Note, Select } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

type ReceiptDetail = components["schemas"]["ReceiptDetailResponse"];

const AUTO = "auto";
const NONE = "none";

/**
 * Which trip a receipt belongs to (F20.1): by its date, as it is unless changed; a trip
 * picked by hand; or none, even inside a trip's dates. A receipt dated within a business
 * trip is asked about first: the employer's, or the user's own. Only the owner sees it.
 */
export const ReceiptTripSelect = observer(function ReceiptTripSelect({
  receipt,
}: {
  receipt: ReceiptDetail;
}) {
  const { tripsStore, receiptStore } = useStores();
  const { t } = useTranslation("trips");

  useEffect(() => {
    if (tripsStore.trips.length === 0) void tripsStore.load();
  }, [tripsStore]);

  if (tripsStore.trips.length === 0 && !receipt.trip && !receipt.trip_question) return null;

  const value = receipt.trip_manual ? (receipt.trip?.id ?? NONE) : AUTO;
  const autoLabel =
    !receipt.trip_manual && receipt.trip
      ? `${t("receipt.auto")}: ${receipt.trip.name}`
      : t("receipt.auto");

  const change = async (next: string) => {
    const placed =
      next === AUTO
        ? await tripsStore.placeReceipt(receipt.id, null, true)
        : await tripsStore.placeReceipt(receipt.id, next === NONE ? null : next);
    if (placed) await receiptStore.reloadReceiptDetail();
  };

  const question = receipt.trip_question;
  return (
    <div className="mb-3 flex flex-col gap-2.5">
      {question && (
        <Note tone="warning">
          <span className="flex flex-col gap-2.5 md:flex-row md:items-center md:justify-between">
            <span>{t("question.business", { name: question.name })}</span>
            <span className="flex gap-2 [&>*]:flex-1 md:[&>*]:flex-none">
              <Button
                size="sm"
                className="min-h-11 md:min-h-0"
                onClick={() => void change(question.id)}
              >
                {t("question.yes")}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="min-h-11 md:min-h-0"
                onClick={() => void change(NONE)}
              >
                {t("question.no")}
              </Button>
            </span>
          </span>
        </Note>
      )}
      <Select
        label={t("receipt.label")}
        value={value}
        className="w-full"
        onChange={(e) => void change(e.target.value)}
      >
        <option value={AUTO}>{autoLabel}</option>
        <option value={NONE}>{t("receipt.none")}</option>
        {tripsStore.trips.map((trip) => (
          <option key={trip.id} value={trip.id}>
            {trip.name}
          </option>
        ))}
      </Select>
    </div>
  );
});

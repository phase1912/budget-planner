import { Plane } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { useStores } from "@/stores/StoreContext";
import { TripChoiceField } from "./TripChoiceField";

/**
 * The wizard's question about a receipt dated within a trip (F20.1).
 *
 * A personal trip takes the receipt unless unticked. A business trip asks outright,
 * because a purchase on it may be the user's own: storing waits for the answer. An
 * upload started from a trip's page only says where the receipt goes.
 */
export const TripQuestion = observer(function TripQuestion({ index }: { index: number }) {
  const { uploadStore } = useStores();
  const { t } = useTranslation("trips");

  if (uploadStore.fromTrip) {
    return (
      <p className="m-0 flex items-center gap-2 rounded-card bg-surface px-4 py-3 text-md">
        <Plane size={16} aria-hidden="true" className="shrink-0 text-muted-foreground" />
        {t("question.fromTrip", { name: uploadStore.fromTrip.name })}
      </p>
    );
  }
  const trip = uploadStore.tripFor(index);
  if (!trip) return null;

  return (
    <TripChoiceField
      trip={trip}
      answer={uploadStore.goesIntoTrip(index)}
      onAnswer={(intoTrip) => {
        uploadStore.answerTrip(index, intoTrip);
      }}
      className={
        trip.kind === "personal"
          ? "rounded-card bg-surface px-4 py-3"
          : "rounded-card border-0 bg-surface px-4 py-3.5"
      }
    />
  );
});

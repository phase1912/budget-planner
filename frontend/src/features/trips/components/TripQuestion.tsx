import { Briefcase, Plane } from "lucide-react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { useStores } from "@/stores/StoreContext";

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
      <p className="m-0 flex items-center gap-2 border-b border-border px-5 py-3 text-md">
        <Plane size={16} aria-hidden="true" className="shrink-0 text-muted-foreground" />
        {t("question.fromTrip", { name: uploadStore.fromTrip.name })}
      </p>
    );
  }
  const trip = uploadStore.tripFor(index);
  if (!trip) return null;
  const answer = uploadStore.goesIntoTrip(index);

  if (trip.kind === "personal") {
    return (
      <label className="flex min-h-11 cursor-pointer items-center gap-3 border-b border-border px-5 py-3 text-md">
        <input
          type="checkbox"
          checked={answer === true}
          onChange={(e) => {
            uploadStore.answerTrip(index, e.target.checked);
          }}
          className="h-5 w-5 shrink-0 cursor-pointer accent-primary"
        />
        <Plane size={16} aria-hidden="true" className="shrink-0 text-muted-foreground" />
        {t("question.personal", { name: trip.name })}
      </label>
    );
  }

  const choice = (value: boolean, label: string) => (
    <button
      type="button"
      aria-pressed={answer === value}
      onClick={() => {
        uploadStore.answerTrip(index, value);
      }}
      className={`min-h-11 flex-1 cursor-pointer rounded-control border px-3 text-md font-semibold transition-colors md:flex-none ${
        answer === value
          ? "border-primary bg-primary/10 text-primary"
          : "border-border bg-background text-foreground hover:bg-surface-hover"
      }`}
    >
      {label}
    </button>
  );

  return (
    <fieldset
      className={`m-0 flex flex-col gap-2.5 border-0 border-b border-border px-5 py-3.5 ${
        answer === undefined ? "bg-tone-warning-bg" : ""
      }`}
    >
      <legend className="float-left flex items-center gap-2 p-0 text-md font-semibold">
        <Briefcase size={16} aria-hidden="true" className="shrink-0" />
        {t("question.business", { name: trip.name })}
      </legend>
      <span className="clear-both text-base text-muted-foreground">
        {t("question.businessHint")}
      </span>
      <div className="flex gap-2">
        {choice(true, t("question.yes"))}
        {choice(false, t("question.no"))}
      </div>
    </fieldset>
  );
});

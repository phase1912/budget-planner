import { Briefcase, Plane } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { Trip } from "@/stores/TripsStore";

/**
 * The question asked of an expense dated within a trip (F20.1): a tick for a personal
 * trip, which takes it unless unticked, and an outright "the company's, or mine?" for a
 * business one, unanswered (undefined) until the user picks. `className` sets its frame.
 */
export function TripChoiceField({
  trip,
  answer,
  onAnswer,
  className = "",
}: {
  trip: Trip;
  answer: boolean | undefined;
  onAnswer: (intoTrip: boolean) => void;
  className?: string;
}) {
  const { t } = useTranslation("trips");

  if (trip.kind === "personal") {
    return (
      <label className={`flex min-h-11 cursor-pointer items-center gap-3 text-md ${className}`}>
        <input
          type="checkbox"
          checked={answer === true}
          onChange={(e) => {
            onAnswer(e.target.checked);
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
        onAnswer(value);
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
      className={`m-0 flex flex-col gap-2.5 ${answer === undefined ? "bg-tone-warning-bg" : ""} ${className}`}
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
}

import { Briefcase, Plane } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { components } from "@/api/schema";

type TripRef = components["schemas"]["TripRef"];

/**
 * A receipt's trip as a list marks it (F20.1): the trip it is on — a business one in its
 * own tone, since its money is out of the budget — or "Business?" while a business trip
 * still asks about it. Nothing for a receipt on no trip.
 */
export function TripLabel({
  trip,
  question,
}: {
  trip?: TripRef | null;
  question?: TripRef | null;
}) {
  const { t } = useTranslation("trips");
  if (!trip && !question) return null;
  const business = trip?.kind === "business";
  const tone = question
    ? "bg-tone-warning-bg text-tone-warning-text"
    : business
      ? "bg-tone-info-bg text-tone-info-text"
      : "bg-tone-accent-bg text-tone-accent-text";
  const Icon = trip && !business ? Plane : Briefcase;
  const text = trip ? trip.name : t("label.question");
  return (
    <span
      title={question ? t("question.business", { name: question.name }) : text}
      className={`inline-flex min-w-0 max-w-full shrink items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-semibold ${tone}`}
    >
      <Icon size={12} aria-hidden="true" className="shrink-0" />
      <span className="truncate">{text}</span>
    </span>
  );
}

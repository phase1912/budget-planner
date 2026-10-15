import { Briefcase, Plane } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { Meter, Pill } from "@/shared/components";
import { PreviewFrame } from "./PreviewFrame";

/** A business trip's settlement with its per diem, and a holiday against its budget. */
export function TripPreview() {
  const { t } = useTranslation("landing");
  return (
    <PreviewFrame>
      <div className="flex flex-col gap-2 border-b border-border pb-3">
        <span className="flex flex-wrap items-center gap-2">
          <Briefcase size={16} className="shrink-0 text-muted-foreground" />
          <span className="text-lg font-bold">{t("preview.trip.name")}</span>
          <Pill size="sm" tone="info">
            {t("preview.trip.kind")}
          </Pill>
        </span>
        <span className="flex items-baseline justify-between gap-3 text-md">
          <span>{t("preview.trip.perDiem")}</span>
          <span className="tabular-nums font-semibold">{formatAmount(132.3)} EUR</span>
        </span>
        <span className="flex items-baseline justify-between gap-3 text-lg font-bold">
          <span>{t("preview.trip.toReimburse")}</span>
          <span className="tabular-nums">{formatAmount(319.4)} PLN</span>
        </span>
      </div>
      <div className="flex flex-col gap-1.5 pt-3">
        <span className="flex items-center gap-2 text-lg font-bold">
          <Plane size={16} className="shrink-0 text-muted-foreground" />
          {t("preview.trip.holiday")}
        </span>
        <Meter value={87} />
        <span className="text-base text-muted-foreground">{t("preview.trip.budgetLeft")}</span>
      </div>
    </PreviewFrame>
  );
}

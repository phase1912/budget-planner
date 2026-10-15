import { Lightbulb } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { Meter } from "@/shared/components";
import { PreviewFrame } from "./PreviewFrame";

/** A goal on pace, with a piece of advice that names a real purchase and what it saves. */
export function GoalPreview() {
  const { t } = useTranslation("landing");
  return (
    <PreviewFrame>
      <div className="flex flex-col gap-1.5 pb-3">
        <span className="text-lg font-bold">{t("preview.goal.name")}</span>
        <Meter value={70} />
        <span className="text-base text-muted-foreground">{t("preview.goal.pace")}</span>
      </div>
      <div className="flex gap-3 rounded-control border border-border p-3">
        <Lightbulb size={18} className="mt-0.5 shrink-0 text-primary" />
        <span className="flex flex-col gap-1">
          <span className="text-md">{t("preview.goal.advice")}</span>
          <span className="text-base font-semibold text-primary">
            {t("preview.goal.saves", { amount: `${formatAmount(96)} PLN` })}
          </span>
        </span>
      </div>
    </PreviewFrame>
  );
}

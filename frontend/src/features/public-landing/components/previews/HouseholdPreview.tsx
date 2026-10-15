import { Lock } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatAmount } from "@/i18n/format";
import { PreviewFrame } from "./PreviewFrame";

const SHARES = [1340, 860];

/** A household's month: who spent what together, and one member's private receipt. */
export function HouseholdPreview() {
  const { t } = useTranslation("landing");
  const members = t("preview.household.members", { returnObjects: true });
  const total = SHARES.reduce((sum, share) => sum + share, 0) + 120;
  return (
    <PreviewFrame>
      <div className="flex items-baseline justify-between gap-3 pb-3">
        <span className="text-lg font-bold">{t("preview.household.name")}</span>
        <span className="text-lg font-bold tabular-nums">{formatAmount(total)} PLN</span>
      </div>
      <span className="text-base text-muted-foreground">{t("preview.household.shared")}</span>
      <ul className="m-0 flex list-none flex-col gap-2.5 p-0 pt-3">
        {members.map((member, i) => (
          <li key={member} className="flex items-center justify-between gap-3 text-md">
            <span className="flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-tone-primary-bg text-base font-semibold text-tone-primary-text">
                {member.charAt(0)}
              </span>
              {member}
            </span>
            <span className="tabular-nums font-semibold">{formatAmount(SHARES[i] ?? 0)}</span>
          </li>
        ))}
        <li className="flex items-center justify-between gap-3 text-md text-muted-foreground">
          <span className="flex items-center gap-2">
            <Lock size={16} className="mx-1.5 shrink-0" />
            {t("preview.household.private")}
          </span>
          <span className="tabular-nums">{formatAmount(120)}</span>
        </li>
      </ul>
    </PreviewFrame>
  );
}

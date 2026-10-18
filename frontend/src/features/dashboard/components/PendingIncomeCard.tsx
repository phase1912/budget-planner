import { Mail, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import type { PendingIncome } from "@/stores/IncomeStore";

const WHOLE = numberFormat({ maximumFractionDigits: 2 });

interface PendingIncomeCardProps {
  pending: PendingIncome;
  currency: string;
  onReview: () => void;
  onDismiss: () => void;
}

/**
 * A payslip or transfer that came in by email (F23.11): what was read, waiting to be
 * checked and added — it counts nowhere until then — or dismissed.
 */
export function PendingIncomeCard({
  pending,
  currency,
  onReview,
  onDismiss,
}: PendingIncomeCardProps) {
  const { t } = useTranslation("dashboard");
  return (
    <section
      aria-label={t("pendingIncome.title")}
      className="flex flex-col gap-3 rounded-card bg-tone-primary-bg px-4 py-3.5"
    >
      <span className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-primary text-primary-foreground">
          <Mail size={20} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-md text-muted-foreground">
            {t("pendingIncome.title")}
            {pending.source ? ` · ${pending.source}` : ""}
          </span>
          <span className="text-xl font-extrabold tabular-nums">
            {pending.amount
              ? `${WHOLE.format(Number(pending.amount))} ${currency}`
              : t("pendingIncome.noAmount")}
          </span>
        </span>
        <button
          type="button"
          aria-label={t("pendingIncome.dismiss")}
          className="-mr-2 -mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-pill text-muted-foreground"
          onClick={onDismiss}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </span>
      <Button size="sm" className="min-h-11" onClick={onReview}>
        {t("pendingIncome.review")}
      </Button>
    </section>
  );
}

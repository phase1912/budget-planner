import { Landmark, Pencil } from "lucide-react";
import { useTranslation } from "react-i18next";

import { dateFormat, numberFormat } from "@/i18n/format";
import type { Balance } from "@/stores/IncomeStore";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "long" });

interface BalanceCardProps {
  balance: Balance | null;
  currency: string;
  onEdit: () => void;
}

/**
 * What the user has now (F23.14): the money on their accounts as they entered it once,
 * moved since by income and counted purchases. Without a start it invites one — and says
 * plainly that it is what is on the accounts today, not income.
 */
export function BalanceCard({ balance, currency, onEdit }: BalanceCardProps) {
  const { t } = useTranslation("dashboard");
  const known = balance?.balance != null;
  return (
    <button
      type="button"
      onClick={onEdit}
      className="flex min-h-16 items-center gap-3.5 rounded-card bg-surface px-4 py-3 text-left shadow-card"
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
        <Landmark size={20} aria-hidden="true" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-base font-medium text-muted-foreground">{t("balance.title")}</span>
        {known ? (
          <span className="text-xl font-bold tabular-nums">
            {WHOLE.format(Number(balance.balance))} {currency}
          </span>
        ) : (
          <span className="text-lg font-semibold text-primary">{t("balance.add")}</span>
        )}
        {known && balance.since && (
          <span className="text-sm text-muted-foreground">
            {t("balance.since", { date: DAY.format(new Date(`${balance.since}T00:00:00`)) })}
          </span>
        )}
      </span>
      <Pencil size={16} className="shrink-0 text-muted-foreground" aria-hidden="true" />
    </button>
  );
}

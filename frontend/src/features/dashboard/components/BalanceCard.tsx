import { ChevronRight, CircleAlert, Landmark, Pencil } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/shared/components";
import { dateFormat, numberFormat } from "@/i18n/format";
import type { BankAccount } from "@/stores/BankAccountsStore";
import type { Balance } from "@/stores/IncomeStore";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const DAY = dateFormat({ day: "numeric", month: "long" });

interface BalanceCardProps {
  balance: Balance | null;
  /** The user's cards below zero (F23.21): each is named, even when the sum is not. */
  overdrawn?: BankAccount[];
  currency: string;
  onEdit: () => void;
  onAddIncome: () => void;
}

/**
 * What the user has now (F23.14): the money on their accounts as they entered it once,
 * moved since by income and counted purchases. Without a start it invites one — and says
 * plainly that it is what is on the accounts today, not income. At zero or below it asks
 * for what is missing instead: such a balance almost always means income not entered,
 * not a debt, so it offers to add income or to set the balance again.
 *
 * Once the user keeps accounts (F23.15) it is their sum, and opens them instead. A card
 * below zero is said plainly (F23.21) — most likely a top-up was not entered — with a way
 * to add what came in or to open the accounts; spending and the budget go on regardless.
 */
export function BalanceCard({
  balance,
  overdrawn = [],
  currency,
  onEdit,
  onAddIncome,
}: BalanceCardProps) {
  const { t } = useTranslation("dashboard");
  const known = balance?.balance != null;

  if (known && balance.from_accounts && overdrawn.length > 0) {
    const first = overdrawn[0];
    return (
      <section
        aria-label={t("balance.title")}
        className="flex flex-col gap-3 rounded-card bg-tone-warning-bg px-4 py-3.5 text-tone-warning-text"
      >
        <span className="flex items-start gap-3">
          <CircleAlert size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
          <span className="flex flex-col gap-1">
            <span className="text-lg font-bold">{t("balance.overdrawnTitle")}</span>
            <span className="text-md tabular-nums">
              {overdrawn.length === 1 && first
                ? t("balance.overdrawnOne", {
                    name: first.name,
                    amount: WHOLE.format(Number(first.balance)),
                    currency,
                  })
                : t("balance.overdrawnMany", { count: overdrawn.length })}
            </span>
          </span>
        </span>
        <span className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <Button size="sm" className="min-h-11" onClick={onAddIncome}>
            {t("balance.topUp")}
          </Button>
          <Link
            to="/accounts"
            className="inline-flex min-h-11 items-center justify-center rounded-control bg-surface px-4 text-md font-bold text-foreground no-underline"
          >
            {t("balance.openAccounts")}
          </Link>
        </span>
      </section>
    );
  }

  if (known && balance.from_accounts) {
    return (
      <Link
        to="/accounts"
        className="flex min-h-16 items-center gap-3.5 rounded-card bg-surface px-4 py-3 text-left text-foreground no-underline"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
          <Landmark size={20} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-base font-medium text-muted-foreground">{t("balance.title")}</span>
          <span className="text-xl font-bold tabular-nums">
            {WHOLE.format(Number(balance.balance))} {currency}
          </span>
          {balance.for_taxes != null && Number(balance.for_taxes) > 0 && (
            <span className="text-md font-semibold text-tone-warning-text tabular-nums">
              {t("balance.forTaxes", { amount: WHOLE.format(Number(balance.for_taxes)), currency })}
            </span>
          )}
          <span className="text-sm text-muted-foreground">{t("balance.accounts")}</span>
        </span>
        <ChevronRight size={18} className="shrink-0 text-muted-foreground" aria-hidden="true" />
      </Link>
    );
  }

  if (known && Number(balance.balance) <= 0) {
    return (
      <section
        aria-label={t("balance.title")}
        className="flex flex-col gap-3 rounded-card bg-tone-warning-bg px-4 py-3.5 text-tone-warning-text"
      >
        <span className="flex items-start gap-3">
          <CircleAlert size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
          <span className="flex flex-col gap-1">
            <span className="text-lg font-bold">{t("balance.emptyTitle")}</span>
            <span className="text-md tabular-nums">
              {t("balance.emptyBody", { amount: WHOLE.format(Number(balance.balance)), currency })}
            </span>
          </span>
        </span>
        <span className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <Button size="sm" className="min-h-11" onClick={onAddIncome}>
            {t("balance.addIncome")}
          </Button>
          <Button variant="secondary" size="sm" className="min-h-11" onClick={onEdit}>
            {t("balance.correct")}
          </Button>
        </span>
      </section>
    );
  }

  return (
    <button
      type="button"
      onClick={onEdit}
      className="flex min-h-16 items-center gap-3.5 rounded-card bg-surface px-4 py-3 text-left"
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
        {known && balance.for_taxes != null && Number(balance.for_taxes) > 0 && (
          <span className="text-md font-semibold text-tone-warning-text tabular-nums">
            {t("balance.forTaxes", { amount: WHOLE.format(Number(balance.for_taxes)), currency })}
          </span>
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

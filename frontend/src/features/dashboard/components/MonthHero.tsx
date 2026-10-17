import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Ring, type RingSegment } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import { categoryColor } from "@/shared/categoryColor";
import type { CategorySpend } from "@/stores/CategoriesStore";
import type { MonthSummary } from "@/stores/BudgetStore";
import type { MonthIncome } from "@/stores/IncomeStore";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const AMOUNT = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });

interface View {
  key: "budget" | "income" | "categories";
  segments: RingSegment[];
  max?: number;
  value: string;
  label: string;
  picture: string;
}

interface MonthHeroProps {
  summary: MonthSummary;
  /** The month's categories: the ring shows them when there is nothing to measure against. */
  spend: CategorySpend[];
  income: MonthIncome | null;
  currency: string;
  onEditIncome: () => void;
  onEditBudget: () => void;
}

/**
 * The first thing Home says (F23.3): the month as a ring that changes view on a tap —
 * what is left of the budget, what is left of the income, where the money went by
 * category — each in its own colour, with the income, the budget and a daily pace beside
 * it. An unfinished month says "so far" (D4). Income and budget are changed right here.
 */
export function MonthHero({
  summary,
  spend,
  income,
  currency,
  onEditIncome,
  onEditBudget,
}: MonthHeroProps) {
  const { t } = useTranslation("dashboard");
  const spent = Number(summary.total);
  const budget = summary.budget_limit == null ? null : Number(summary.budget_limit);
  const earned = income?.total == null ? null : Number(income.total);
  const base = budget ?? earned;
  const left = base === null ? null : base - spent;
  const over = left !== null && left < 0;
  const daysLeft = summary.is_complete ? 0 : summary.days_in_month - summary.days_elapsed + 1;
  const spentLabel = summary.is_complete ? t("spent") : t("spentSoFar");

  // The ring's views, each in its own colour of the palette; a tap moves to the next.
  const views: View[] = [];
  if (budget !== null) {
    const rest = budget - spent;
    views.push({
      key: "budget",
      segments: [{ value: spent, color: rest < 0 ? "var(--color-error)" : "var(--color-primary)" }],
      max: budget,
      value: WHOLE.format(Math.abs(rest)),
      label: rest < 0 ? t("hero.over") : t("hero.leftOfBudget"),
      picture: t("hero.ring", { spent: AMOUNT.format(spent), of: AMOUNT.format(budget), currency }),
    });
  }
  if (earned !== null) {
    const rest = earned - spent;
    views.push({
      key: "income",
      segments: [{ value: spent, color: rest < 0 ? "var(--color-error)" : "var(--cat-dining)" }],
      max: earned,
      value: WHOLE.format(Math.abs(rest)),
      label: rest < 0 ? t("hero.overIncome") : t("hero.leftOfIncome"),
      picture: t("hero.ringIncome", {
        spent: AMOUNT.format(spent),
        of: AMOUNT.format(earned),
        currency,
      }),
    });
  }
  views.push({
    key: "categories",
    segments: spend.map((c) => ({
      value: Number(c.total_amount),
      color: categoryColor(c.name ?? ""),
    })),
    value: WHOLE.format(spent),
    label: spentLabel,
    picture: t("hero.ringCategories", { spent: AMOUNT.format(spent), currency }),
  });
  const [at, setAt] = useState(0);
  const view = views[at % views.length] ?? views[views.length - 1];

  const facts: {
    key: string;
    label: string;
    value: string;
    action?: () => void;
    muted?: boolean;
  }[] = [
    {
      key: "income",
      label:
        income?.entered === false && earned !== null ? t("hero.incomeUsual") : t("hero.income"),
      value: earned === null ? t("hero.add") : `${WHOLE.format(earned)} ${currency}`,
      action: onEditIncome,
      muted: earned === null,
    },
    {
      key: "budget",
      label: t("hero.budget"),
      value: budget === null ? t("hero.set") : `${WHOLE.format(budget)} ${currency}`,
      action: onEditBudget,
      muted: budget === null,
    },
  ];
  if (left !== null && !over && daysLeft > 0) {
    facts.push({
      key: "pace",
      label: t("hero.daysLeft", { count: daysLeft }),
      value: t("hero.perDay", { amount: WHOLE.format(left / daysLeft), currency }),
    });
  } else if (summary.is_complete && earned !== null) {
    facts.push({
      key: "saved",
      label: t("hero.kept"),
      value: `${WHOLE.format(earned - spent)} ${currency}`,
    });
  }

  return (
    <section
      aria-label={t("hero.label")}
      className="flex flex-col items-center gap-5 rounded-card bg-surface p-5 shadow-card md:flex-row md:gap-8 md:p-7"
    >
      <div className="flex flex-col items-center gap-2.5">
        <button
          type="button"
          onClick={() => {
            setAt((i) => (i + 1) % views.length);
          }}
          aria-label={`${view?.picture ?? ""}. ${t("hero.next")}`}
          className="rounded-pill"
        >
          <Ring
            segments={view?.segments ?? []}
            max={view?.max}
            className="h-44 w-44 md:h-48 md:w-48"
            thickness={0.16}
            label={view?.picture ?? ""}
          >
            <span className="text-[28px] font-bold leading-tight tracking-tight tabular-nums md:text-[32px]">
              {view?.value}
            </span>
            <span className="text-sm font-semibold text-muted-foreground">{currency}</span>
            <span className="mt-1 max-w-[7.5rem] text-sm font-medium leading-snug text-muted-foreground">
              {view?.label}
            </span>
          </Ring>
        </button>
        {views.length > 1 && (
          <span className="flex gap-1.5" aria-hidden="true">
            {views.map((v, i) => (
              <span
                key={v.key}
                className={`h-1.5 rounded-pill transition-all ${
                  i === at % views.length ? "w-5 bg-primary" : "w-1.5 bg-border-strong"
                }`}
              />
            ))}
          </span>
        )}
      </div>
      <div className="flex w-full flex-col gap-2.5">
        <dl className="m-0 grid w-full grid-cols-1 gap-2.5">
          {facts.map((fact) => {
            const body = (
              <>
                <dt className="text-base font-medium text-muted-foreground">{fact.label}</dt>
                <dd
                  className={`m-0 text-xl font-bold tabular-nums ${fact.muted ? "text-primary" : ""}`}
                >
                  {fact.value}
                </dd>
              </>
            );
            return fact.action ? (
              <button
                key={fact.key}
                type="button"
                onClick={fact.action}
                className="flex min-h-14 items-center justify-between gap-3 rounded-control border border-border px-4 py-2.5 text-left transition-colors hover:bg-tone-primary-bg"
              >
                {body}
              </button>
            ) : (
              <div
                key={fact.key}
                className="flex min-h-14 items-center justify-between gap-3 rounded-control border border-border px-4 py-2.5"
              >
                {body}
              </div>
            );
          })}
        </dl>
        <p className="m-0 text-base text-muted-foreground tabular-nums">
          {t("days", {
            elapsed: summary.is_complete ? summary.days_in_month : summary.days_elapsed,
            days: summary.days_in_month,
          })}{" "}
          · {t("receipts", { count: summary.receipt_count })}
        </p>
      </div>
    </section>
  );
}

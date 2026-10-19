import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import {
  AmountDialog,
  ErrorState,
  LoadingState,
  Note,
  Ring,
  SegmentedControl,
} from "@/shared/components";
import { categoryName } from "@/shared/categoryName";
import { numberFormat } from "@/i18n/format";
import { isoDay } from "@/stores/StatisticsStore";
import type { HouseholdStatistics } from "@/stores/HouseholdStore";
import { useStores } from "@/stores/StoreContext";
import { memberColours } from "../memberColours";
import { HouseholdDailyBars } from "./HouseholdDailyBars";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const PERCENT = numberFormat({ style: "percent", maximumFractionDigits: 0 });

type Chart = "share" | "categories" | "days";

const pad = (n: number) => String(n).padStart(2, "0");

type CategoryRow = HouseholdStatistics["categories"][number];

/** Items with no category and the built-in "Uncategorized" are one row to a reader. */
function uncategorisedAsOne(rows: readonly CategoryRow[]): CategoryRow[] {
  const isNone = (c: CategoryRow) =>
    c.category_id === null || (c.owner_id === null && c.name === "Uncategorized");
  const none = rows.filter(isNone);
  const base = none.find((c) => c.category_id !== null);
  if (none.length < 2 || !base) return [...rows];
  const parts = new Map<string, number>();
  for (const m of none.flatMap((c) => c.members)) {
    parts.set(m.user_id, (parts.get(m.user_id) ?? 0) + Number(m.total));
  }
  const merged: CategoryRow = {
    ...base,
    item_count: none.reduce((n, c) => n + c.item_count, 0),
    total: String(none.reduce((n, c) => n + Number(c.total), 0)),
    members: [...parts].map(([user_id, total]) => ({ user_id, total: String(total) })),
  };
  return [...rows.filter((c) => !isNone(c)), merged].sort(
    (a, b) => Number(b.total) - Number(a.total),
  );
}

/**
 * The family's month on Home (F12.5, F12.9, canvas F_Home): what is left together — of
 * the household budget, or else of the shared income after the shared bills — the shared
 * money of the month, and who spends what: each member's share as a ring, by category or
 * by day. Another member's private receipts count as one sum and never say what or when
 * (ADR-0017). An adult changes the household budget here (F12.8), unless the owner keeps
 * it to themselves (F12.10).
 */
export const HouseholdMonthView = observer(function HouseholdMonthView({
  year,
  month,
  currency,
}: {
  year: number;
  month: number;
  currency: string;
}) {
  const { householdStore, authStore } = useStores();
  const { t } = useTranslation("dashboard");
  const [chart, setChart] = useState<Chart>("share");
  const [editingBudget, setEditingBudget] = useState(false);
  const summary = householdStore.month;
  const statistics = householdStore.statistics;
  const { error, isLoading } = householdStore.monthState;
  const start = `${String(year)}-${pad(month)}-01`;
  const end = isoDay(new Date(year, month, 0));

  useEffect(() => {
    void householdStore.loadMonth(year, month);
    void householdStore.loadStatistics(start, end);
    void householdStore.loadDaily(start, end);
  }, [householdStore, year, month, start, end]);

  if (!summary) {
    return error ? (
      <ErrorState layout="banner" title={t("household.loadFailed")} message={error} />
    ) : (
      <LoadingState title={t("household.loading")} />
    );
  }

  const me = authStore.user?.id;
  const spent = Number(summary.total);
  const income = Number(summary.shared_income);
  const bills = Number(summary.shared_bills);
  // The month answers with the budget it is measured against.
  const budget = summary.limit?.limit ?? null;
  const base = budget !== null ? Number(budget) : income > 0 ? income - bills : null;
  const left = base === null ? null : base - spent;
  // The viewer first, as on every family chart.
  const people = [...summary.members].sort(
    (a, b) => Number(b.user_id === me) - Number(a.user_id === me),
  );
  const colourOf = memberColours(
    summary.members.map((m) => m.user_id),
    me,
  );
  const nameOf = (id: string, first: string) => (id === me ? t("household.you") : first);
  const othersPrivate = summary.members
    .filter((m) => m.user_id !== me)
    .reduce((sum, m) => sum + Number(m.private_total), 0);
  const facts = [
    { key: "income", label: t("household.income"), value: income, shared: true },
    { key: "bills", label: t("household.bills"), value: bills, shared: true },
  ];

  return (
    <>
      <section
        aria-label={t("household.ourMonth")}
        aria-busy={isLoading}
        className={`flex items-center gap-4 rounded-hero bg-surface p-4 transition-opacity md:gap-8 md:p-6 ${isLoading ? "opacity-60" : ""}`}
      >
        <Ring
          segments={[
            {
              value: spent,
              color: left !== null && left < 0 ? "var(--color-error)" : "var(--color-primary)",
            },
          ]}
          max={base ?? spent}
          className="h-34 w-34 shrink-0 md:h-44 md:w-44"
          thickness={0.2}
          label={t("household.ring", { spent: WHOLE.format(spent), currency })}
        >
          <span className="text-xl font-extrabold tabular-nums md:text-3xl">
            {WHOLE.format(Math.abs(left ?? spent))}
          </span>
          <span className="max-w-[6.5rem] text-xs font-semibold leading-snug text-muted-foreground md:text-sm">
            {left === null
              ? t("household.spentTogetherSoFar")
              : left < 0
                ? t("household.over")
                : t("household.leftTogether")}
          </span>
        </Ring>
        <dl className="m-0 flex min-w-0 flex-1 flex-col gap-1">
          {facts.map((fact) => (
            <div key={fact.key} className="flex min-h-11 flex-col justify-center">
              <dt className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
                {fact.label}
                <span className="rounded-pill bg-tone-primary-bg px-1.5 text-xs font-extrabold text-primary">
                  {t("household.shared")}
                </span>
              </dt>
              <dd className="m-0 text-lg font-extrabold tabular-nums md:text-xl">
                {WHOLE.format(fact.value)} {currency}
              </dd>
            </div>
          ))}
          {householdStore.mayChangeBudget ? (
            <button
              type="button"
              onClick={() => {
                setEditingBudget(true);
              }}
              className="flex min-h-11 flex-col items-start justify-center rounded-chip text-left"
            >
              <span className="text-sm font-semibold text-muted-foreground">
                {t("household.budget")}
              </span>
              <span
                className={`text-lg font-extrabold tabular-nums md:text-xl ${budget === null ? "text-primary" : ""}`}
              >
                {budget === null ? t("hero.set") : `${WHOLE.format(Number(budget))} ${currency}`}
              </span>
            </button>
          ) : (
            // A child, or an adult while the owner keeps the budget, only reads it (F12.10).
            <div className="flex min-h-11 flex-col justify-center">
              <dt className="text-sm font-semibold text-muted-foreground">
                {t("household.budget")}
              </dt>
              <dd className="m-0 text-lg font-extrabold tabular-nums md:text-xl">
                {budget === null ? "—" : `${WHOLE.format(Number(budget))} ${currency}`}
              </dd>
            </div>
          )}
        </dl>
      </section>

      {summary.excluded_count > 0 && (
        <Note tone="warning">
          {t("household.underReview", {
            count: summary.excluded_count,
            amount: WHOLE.format(Number(summary.excluded_amount)),
            currency,
          })}
        </Note>
      )}

      <section
        aria-labelledby="who-spends"
        className="flex flex-col gap-4 rounded-hero bg-surface p-4 md:p-6"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h2 id="who-spends" className="m-0 text-xl font-extrabold">
            {t("household.who")}
          </h2>
          <span className="text-md font-semibold text-muted-foreground tabular-nums">
            {t("household.together", { amount: WHOLE.format(spent), currency })}
          </span>
        </div>
        <div className="on-surface">
          <SegmentedControl<Chart>
            label={t("household.who")}
            fill
            size="sm"
            value={chart}
            onChange={setChart}
            options={[
              { value: "share", label: t("household.charts.share") },
              { value: "categories", label: t("household.charts.categories") },
              { value: "days", label: t("household.charts.days") },
            ]}
          />
        </div>

        {chart === "share" && (
          <div className="flex items-center gap-5">
            <Ring
              segments={people.map((m) => ({
                value: Number(m.total),
                color: colourOf.get(m.user_id) ?? "var(--cat-other)",
              }))}
              className="h-30 w-30 shrink-0"
              thickness={0.3}
              label={t("household.who")}
            >
              <span className="text-lg font-extrabold tabular-nums">
                {PERCENT.format(
                  spent > 0
                    ? Number(summary.members.find((m) => m.user_id === me)?.total ?? 0) / spent
                    : 0,
                )}
              </span>
              <span className="text-xs font-semibold text-muted-foreground">
                {t("household.you")}
              </span>
            </Ring>
            <ul className="m-0 flex min-w-0 flex-1 list-none flex-col gap-2.5 p-0">
              {people.map((m) => (
                <li key={m.user_id} className="flex flex-col gap-0.5">
                  <span className="flex items-center gap-2 text-lg font-extrabold">
                    <span
                      aria-hidden="true"
                      className="h-2.5 w-2.5 shrink-0 rounded-pill"
                      style={{ background: colourOf.get(m.user_id) }}
                    />
                    <span className="truncate">{nameOf(m.user_id, m.first_name)}</span>
                    <span className="tabular-nums">
                      {PERCENT.format(spent > 0 ? Number(m.total) / spent : 0)}
                    </span>
                  </span>
                  <span className="pl-4.5 text-md text-muted-foreground tabular-nums">
                    {WHOLE.format(Number(m.total))} {currency}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {chart === "categories" && (
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {uncategorisedAsOne(statistics?.categories ?? [])
              .slice(0, 6)
              .map((c) => {
                const whole = Number(c.total);
                return (
                  <li key={c.category_id ?? "none"} className="flex flex-col gap-1.5">
                    <span className="flex justify-between gap-3 text-md font-bold">
                      <span className="truncate">{categoryName(c.name ?? "Uncategorized")}</span>
                      <span className="shrink-0 text-muted-foreground tabular-nums">
                        {people
                          .map((m) => {
                            const part = Number(
                              c.members.find((x) => x.user_id === m.user_id)?.total ?? 0,
                            );
                            return `${nameOf(m.user_id, m.first_name)} ${PERCENT.format(whole > 0 ? part / whole : 0)}`;
                          })
                          .join(" · ")}
                      </span>
                    </span>
                    <span
                      className="flex h-2.5 overflow-hidden rounded-pill bg-muted"
                      aria-hidden="true"
                    >
                      {people.map((m) => {
                        const part = Number(
                          c.members.find((x) => x.user_id === m.user_id)?.total ?? 0,
                        );
                        return (
                          <span
                            key={m.user_id}
                            style={{
                              width: `${String(whole > 0 ? (part / whole) * 100 : 0)}%`,
                              background: colourOf.get(m.user_id),
                            }}
                          />
                        );
                      })}
                    </span>
                  </li>
                );
              })}
          </ul>
        )}

        {chart === "days" && (
          <HouseholdDailyBars currency={currency} today={isoDay(new Date())} bare />
        )}

        {othersPrivate > 0 && (
          <p className="m-0 text-sm leading-relaxed text-muted-foreground tabular-nums">
            {t("household.othersPrivate", { amount: WHOLE.format(othersPrivate), currency })}
          </p>
        )}
      </section>

      {editingBudget && (
        <AmountDialog
          title={t("household.budget")}
          label={t("household.budget")}
          hint={t("household.budgetHint")}
          initial={budget ?? ""}
          currency={currency}
          allowEmpty
          onSave={async (amount) => {
            const ok = await householdStore.setBudget(amount === "" ? null : amount);
            if (ok) void householdStore.loadMonth(year, month);
            return ok;
          }}
          onClose={() => {
            setEditingBudget(false);
          }}
        />
      )}
    </>
  );
});

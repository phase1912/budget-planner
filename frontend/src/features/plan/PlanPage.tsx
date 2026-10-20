import { useEffect, useState, type ReactNode } from "react";
import { observer } from "mobx-react-lite";
import { Briefcase, ChevronRight, Landmark, Palmtree, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AmountDialog, Button } from "@/shared/components";
import { dateFormat, numberFormat } from "@/i18n/format";
import type { IncomeEntry } from "@/stores/IncomeStore";
import { useStores } from "@/stores/StoreContext";
import { IncomeDialog } from "./IncomeDialog";
import { PlanGoals } from "./PlanGoals";
import { RegularIncomes } from "@/features/profile/components/RegularIncomes";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const MONTH = dateFormat({ month: "long", year: "numeric" });
const DAY = dateFormat({ day: "numeric", month: "short" });

/**
 * Plan (F23.2): money coming in this month, the monthly budget, holidays, business trips
 * for those who travel for work, and goals — what the user sets up, where the other tabs
 * show what happened.
 */
export const PlanPage = observer(function PlanPage() {
  const { authStore, incomeStore, budgetStore, tripsStore, goalsStore, profileStore } = useStores();
  const { t } = useTranslation("plan");
  const [incomeEntry, setIncomeEntry] = useState<IncomeEntry | null | "new">(null);
  const [editingBudget, setEditingBudget] = useState(false);
  const [payingTaxes, setPayingTaxes] = useState(false);
  const user = authStore.user;
  const currency = user?.currency ?? "PLN";
  const { year, month } = budgetStore.current;

  useEffect(() => {
    void incomeStore.load(year, month);
    void budgetStore.open();
    void tripsStore.load();
    void goalsStore.load();
  }, [incomeStore, budgetStore, tripsStore, goalsStore, year, month]);

  const income = incomeStore.month;
  // A regular income or bill changed in place: the month's figures and the balance follow.
  const refresh = () => {
    void incomeStore.load(year, month);
    void incomeStore.loadBalance(budgetStore.today);
  };
  const summary = budgetStore.summary;
  const budget = user?.budget_limit == null ? null : Number(user.budget_limit);
  const spent = summary?.month === month ? Number(summary.total) : 0;
  const holidays = tripsStore.trips.filter((trip) => trip.kind === "personal");
  // The bar measures spending against what is the user's to keep (F23.16).
  const kept = income?.net ?? income?.total;
  const incomeTotal = kept == null ? null : Number(kept);
  const paysOwnTaxes = user?.pays_own_taxes === true;
  const bills = Number(income?.bills_total ?? 0);
  const business = tripsStore.trips.filter((trip) => trip.kind === "business");

  return (
    <div className="mx-auto grid w-full max-w-3xl gap-4 py-4 md:gap-5 md:py-2 lg:max-w-[1100px] lg:grid-cols-2 lg:items-start">
      <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em] lg:col-span-2">{t("title")}</h1>

      <Section
        title={t("income.title")}
        aside={
          <span className="text-xl font-bold tabular-nums">
            {income?.total != null ? `${WHOLE.format(Number(income.total))} ${currency}` : "—"}
          </span>
        }
      >
        {incomeTotal !== null && incomeTotal > 0 && (
          <>
            {/* Spent, then the month's bills (F23.18), then what is still free — plan.html. */}
            <span className="flex h-3.5 overflow-hidden rounded-pill bg-muted" aria-hidden="true">
              <span
                className={spent + bills > incomeTotal ? "bg-error" : "bg-primary"}
                style={{ width: `${String(Math.min(100, (spent / incomeTotal) * 100))}%` }}
              />
              <span
                className="bg-[var(--cat-utilities)]"
                style={{
                  width: `${String(Math.max(0, Math.min(100 - (spent / incomeTotal) * 100, (bills / incomeTotal) * 100)))}%`,
                }}
              />
            </span>
            <span className="flex flex-wrap gap-x-4 gap-y-1 text-sm font-bold">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-pill bg-primary" />
                {t("income.spent", { amount: WHOLE.format(spent) })}
              </span>
              {bills > 0 && (
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-pill bg-[var(--cat-utilities)]" />
                  {t("income.bills", { amount: WHOLE.format(bills) })}
                </span>
              )}
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="h-2 w-2 rounded-pill bg-muted" />
                {t("income.free", {
                  amount: WHOLE.format(Math.max(0, incomeTotal - spent - bills)),
                })}
              </span>
            </span>
          </>
        )}
        {paysOwnTaxes && income?.total != null && (
          <dl className="on-surface m-0 grid grid-cols-3 gap-2">
            {[
              [t("income.gross"), income.total],
              [t("income.taxes"), income.taxes],
              [t("income.net"), income.net ?? income.total],
            ].map(([label, value]) => (
              <div key={label} className="flex flex-col gap-0.5 rounded-control control-fill p-2.5">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="m-0 text-lg font-extrabold tabular-nums">
                  {WHOLE.format(Number(value))}
                </dd>
              </div>
            ))}
          </dl>
        )}
        {paysOwnTaxes && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-base text-muted-foreground tabular-nums">
              {t("income.taxesPaid", {
                amount: WHOLE.format(Number(income?.taxes_paid ?? 0)),
                currency,
              })}
            </span>
            <Button
              variant="secondary"
              size="sm"
              className="min-h-11"
              onClick={() => {
                setPayingTaxes(true);
              }}
            >
              {t("income.payTaxes")}
            </Button>
          </div>
        )}
        <span className="text-sm font-bold tracking-[0.06em] text-muted-foreground uppercase">
          {t("income.regular")}
        </span>
        {income?.regular.length === 0 && (
          <p className="m-0 text-base text-muted-foreground">
            {MONTH.format(new Date(year, month - 1, 1))} ·{" "}
            {user?.usual_income != null
              ? t("income.usual", { amount: WHOLE.format(Number(user.usual_income)), currency })
              : t("income.usualNone")}
          </p>
        )}
        <RegularIncomes kind="income" onChanged={refresh} />
        <span className="text-sm font-bold tracking-[0.06em] text-muted-foreground uppercase">
          {t("income.extra")}
        </span>
        {income && income.entries.length > 0 ? (
          <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
            {income.entries.map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  onClick={() => {
                    setIncomeEntry(entry);
                  }}
                  className="flex min-h-14 w-full items-center gap-3 py-2 text-left"
                >
                  <span className="flex flex-1 flex-col">
                    <span className="text-lg font-semibold">{entry.source}</span>
                    <span className="text-base text-muted-foreground">
                      {DAY.format(new Date(`${entry.received_on}T00:00:00`))} ·{" "}
                      {t(`income.kinds.${entry.kind}`)}
                      {paysOwnTaxes && entry.taxed && ` · ${t("income.taxedShort")}`}
                    </span>
                  </span>
                  <span className="text-lg font-bold tabular-nums">
                    {WHOLE.format(Number(entry.amount))} {currency}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="m-0 text-md text-muted-foreground">{t("income.none")}</p>
        )}
        <AddButton
          onClick={() => {
            setIncomeEntry("new");
          }}
        >
          {t("income.add")}
        </AddButton>
        <span className="border-t border-border pt-3 text-sm font-bold tracking-[0.06em] text-muted-foreground uppercase">
          {t("income.billsTitle")}
        </span>
        <RegularIncomes kind="bill" onChanged={refresh} />
      </Section>

      {/* Where the money is (F23.15): every account, the family's included. */}
      <Link
        to="/accounts"
        className="flex min-h-16 min-w-0 items-center gap-3.5 rounded-card bg-surface px-4 py-3 text-foreground no-underline"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
          <Landmark size={20} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-lg font-extrabold">{t("accounts.title")}</span>
          <span className="text-md text-muted-foreground">{t("accounts.hint")}</span>
        </span>
        <ChevronRight size={18} aria-hidden="true" className="shrink-0 text-muted-foreground" />
      </Link>

      <Section
        title={t("budget.title")}
        aside={
          <button
            type="button"
            onClick={() => {
              setEditingBudget(true);
            }}
            className="min-h-11 text-xl font-bold text-primary tabular-nums"
          >
            {budget === null ? t("budget.set") : `${WHOLE.format(budget)} ${currency}`}
          </button>
        }
      >
        {budget !== null ? (
          <>
            <span className="h-2.5 overflow-hidden rounded-pill bg-muted" aria-hidden="true">
              <span
                className={`block h-2.5 rounded-pill ${spent > budget ? "bg-error" : "bg-primary"}`}
                style={{ width: `${String(Math.min(100, (spent / budget) * 100))}%` }}
              />
            </span>
            <p className="m-0 text-base text-muted-foreground tabular-nums">
              {t("budget.spent", {
                spent: WHOLE.format(spent),
                budget: WHOLE.format(budget),
                currency,
              })}
            </p>
          </>
        ) : (
          <p className="m-0 text-md text-muted-foreground">{t("budget.none")}</p>
        )}
      </Section>

      <Section title={t("holidays.title")}>
        {holidays.length === 0 ? (
          <p className="m-0 text-md text-muted-foreground">{t("holidays.none")}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
            {holidays.slice(0, 3).map((trip, index) => {
              const total = Number(trip.total);
              const tripBudget = trip.budget == null ? null : Number(trip.budget);
              return (
                <li key={trip.id}>
                  <Link
                    to={`/trips/${trip.id}`}
                    className={`flex flex-col gap-2 rounded-card p-4 ${
                      index === 0
                        ? "bg-primary text-primary-foreground"
                        : "bg-tone-primary-bg text-foreground"
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <Palmtree size={20} className="shrink-0" aria-hidden="true" />
                      <span className="flex-1 truncate text-xl font-extrabold">{trip.name}</span>
                      <span className="text-base opacity-80">
                        {DAY.format(new Date(`${trip.start_date}T00:00:00`))} –{" "}
                        {DAY.format(new Date(`${trip.end_date}T00:00:00`))}
                      </span>
                    </span>
                    {tripBudget !== null && (
                      <span
                        className="h-2 overflow-hidden rounded-pill bg-surface"
                        aria-hidden="true"
                      >
                        <span
                          className="block h-2 rounded-pill bg-primary"
                          style={{ width: `${String(Math.min(100, (total / tripBudget) * 100))}%` }}
                        />
                      </span>
                    )}
                    <span className="text-base font-semibold tabular-nums">
                      {trip.budget_left != null
                        ? t("holidays.left", {
                            amount: WHOLE.format(Number(trip.budget_left)),
                            currency,
                          })
                        : t("holidays.spent", { amount: WHOLE.format(total), currency })}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
        <div className="flex flex-col gap-2 md:flex-row md:justify-between">
          <AddButton to="/trips?kind=personal&new=1">{t("holidays.new")}</AddButton>
          {holidays.length > 0 && (
            <Link to="/trips?kind=personal" className="min-h-11 text-md font-semibold text-primary">
              {t("holidays.all")}
            </Link>
          )}
        </div>
      </Section>

      {user?.travels_for_work === true && (
        <Link
          to="/trips?kind=business"
          className="flex min-h-16 items-center gap-3.5 rounded-card bg-surface px-4 py-3 text-foreground"
        >
          <Briefcase size={20} className="shrink-0 text-primary" aria-hidden="true" />
          <span className="flex flex-1 flex-col">
            <span className="text-lg font-bold">{t("work.title")}</span>
            <span className="text-base text-muted-foreground">
              {t("work.count", { count: business.length })}
            </span>
          </span>
          <ChevronRight size={18} aria-hidden="true" />
        </Link>
      )}

      <Section title={t("goals.title")}>
        <PlanGoals
          currency={currency}
          freeThisMonth={incomeTotal === null ? null : incomeTotal - spent - bills}
        />
      </Section>

      {incomeEntry !== null && (
        <IncomeDialog
          entry={incomeEntry === "new" ? null : incomeEntry}
          defaultDay={budgetStore.today}
          onClose={() => {
            setIncomeEntry(null);
          }}
          onSaved={() => {
            void incomeStore.load(year, month);
            void incomeStore.loadBalance(budgetStore.today);
          }}
        />
      )}
      {payingTaxes && (
        <AmountDialog
          title={t("income.payTaxes")}
          label={t("income.paidAmount")}
          hint={t("income.paidHint")}
          initial={income?.taxes != null && Number(income.taxes) > 0 ? income.taxes : ""}
          currency={currency}
          onSave={(amount) => incomeStore.payTaxes(amount, budgetStore.today, { year, month })}
          onClose={() => {
            setPayingTaxes(false);
          }}
        />
      )}
      {editingBudget && (
        <AmountDialog
          title={t("budget.title")}
          label={t("budget.title")}
          initial={user?.budget_limit ?? ""}
          currency={currency}
          allowEmpty
          onSave={(amount) =>
            profileStore.saveQuietly({ budget_limit: amount === "" ? null : amount })
          }
          onClose={() => {
            setEditingBudget(false);
          }}
        />
      )}
    </div>
  );
});

function Section({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="on-surface flex flex-col gap-3 rounded-card bg-surface p-4 md:p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 text-lg font-extrabold">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

function AddButton({
  children,
  onClick,
  to,
}: {
  children: ReactNode;
  onClick?: () => void;
  to?: string;
}) {
  const className =
    "inline-flex min-h-11 items-center gap-1.5 self-start text-md font-semibold text-primary";
  return to ? (
    <Link to={to} className={className}>
      <Plus size={16} aria-hidden="true" />
      {children}
    </Link>
  ) : (
    <button type="button" onClick={onClick} className={className}>
      <Plus size={16} aria-hidden="true" />
      {children}
    </button>
  );
}

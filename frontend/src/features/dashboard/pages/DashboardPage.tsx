import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { useStores } from "@/stores/StoreContext";
import { monthRange } from "@/stores/BudgetStore";
import { AmountDialog, ErrorState, LoadingState, Note } from "@/shared/components";
import { MonthTrips } from "@/features/trips/components/MonthTrips";
import { DeleteReceiptDialog } from "@/features/receipts/components/DeleteReceiptDialog";
import { EditReceiptDialog } from "@/features/receipts/components/EditReceiptDialog";
import { ReceiptDetailModal } from "@/features/receipts/components/ReceiptDetailModal";
import { AtRiskWarnings } from "@/features/goals/components/AtRiskWarnings";
import { InstallHint } from "@/features/install/InstallHint";
import { BalanceCard } from "../components/BalanceCard";
import { PaydayPrompt } from "../components/PaydayPrompt";
import { PendingIncomeCard } from "../components/PendingIncomeCard";
import { IncomeDialog } from "@/features/plan/IncomeDialog";
import { paydayDue } from "@/stores/IncomeStore";
import { CategoryTiles } from "../components/CategoryTiles";
import { MonthHero } from "../components/MonthHero";
import { HomeHeader } from "../components/HomeHeader";
import { PriceInsight } from "../components/PriceInsight";
import { RecentPurchases } from "../components/RecentPurchases";
import { WelcomePanel } from "../components/WelcomePanel";
import { HouseholdMonthView } from "@/features/household/components/HouseholdMonthView";
import { HouseholdViewSwitch } from "@/features/household/components/HouseholdViewSwitch";
import { numberFormat, dateFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const MONTH = dateFormat({ month: "long" });
const AMOUNT = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Home (F23.3, was the dashboard of F6.1–F6.7): what is left to spend this month as a
 * ring, income and budget changed in place, the lines waiting for a category, where the
 * money went as coloured tiles, and the month's receipts. A user with no receipts yet sees
 * the welcome instead.
 *
 * The month's rules stay as they were: the figure counts receipts by their date (D1, D2),
 * receipts held for review are left out and named beneath it (D3), an unfinished month
 * says "so far" (D4), a corrected receipt refetches the month (D6), and with a budget the
 * month reads against it (D7).
 */
export const DashboardPage = observer(function DashboardPage() {
  const {
    budgetStore,
    authStore,
    receiptStore,
    householdStore,
    incomeStore,
    categoriesStore,
    profileStore,
    productsStore,
  } = useStores();
  const { summary, error } = budgetStore;
  const { t } = useTranslation("dashboard");
  const [editing, setEditing] = useState<"income" | "budget" | "balance" | "received" | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [reviewing, setReviewing] = useState<string | null>(null);

  useEffect(() => {
    void budgetStore.open();
    void householdStore.load();
    void categoriesStore.loadReviewCount();
    void productsStore.loadOverview();
    void incomeStore.loadPending();
  }, [budgetStore, householdStore, categoriesStore, productsStore, incomeStore]);

  const { year, month } = budgetStore;
  useEffect(() => {
    void incomeStore.load(year, month);
  }, [incomeStore, year, month]);
  const today = budgetStore.today;
  const receiptsKnown = budgetStore.receiptsInMonth;
  useEffect(() => {
    void incomeStore.loadBalance(today);
  }, [incomeStore, today, receiptsKnown]);

  if (!summary) {
    return (
      <div className="flex-grow flex flex-col items-center py-10 px-4 md:px-8">
        <div className="w-full max-w-[960px]">
          {error ? (
            <ErrorState layout="banner" title={t("loadFailed")} message={error} />
          ) : (
            <LoadingState title={t("loading")} />
          )}
        </div>
      </div>
    );
  }

  // A new member has no receipts yet but already has the household's month to look at.
  if (!summary.has_receipts && !householdStore.shared) return <WelcomePanel />;

  const selected = new Date(budgetStore.year, budgetStore.month - 1, 1);
  const currency = authStore.user?.currency ?? "PLN";
  const heldOutWorth = t("heldOutWorth", {
    receipts: t("receipts", { count: summary.excluded_count }),
    amount: AMOUNT.format(Number(summary.excluded_amount)),
    currency,
  });
  const entries = incomeStore.month?.entries ?? [];
  const shown = { year, month };
  const running = year === budgetStore.current.year && month === budgetStore.current.month;
  const askPayday = running && paydayDue(today, authStore.user?.payday, incomeStore.month);
  const usual = incomeStore.month?.total ?? null;
  const reviewCount = categoriesStore.reviewCount;

  return (
    <div className="flex-grow flex flex-col items-center pb-4">
      <div className="w-full max-w-[960px] flex flex-col gap-4.5 md:gap-5">
        <HomeHeader isComplete={summary.is_complete} />

        <HouseholdViewSwitch />
        <InstallHint />
        <AtRiskWarnings linkToGoals />

        {householdStore.showingHousehold ? (
          <HouseholdMonthView year={year} month={month} currency={currency} />
        ) : (
          <>
            {error && <ErrorState layout="banner" title={t("loadFailed")} message={error} />}

            <div className="grid gap-4.5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:items-start">
              <MonthHero
                summary={summary}
                spend={budgetStore.spend}
                income={incomeStore.month}
                currency={currency}
                onEditIncome={() => {
                  setEditing("income");
                }}
                onEditBudget={() => {
                  setEditing("budget");
                }}
              />
              <div className="flex flex-col gap-3">
                {reviewCount > 0 && (
                  <Link
                    to="/categories"
                    className="flex min-h-14 items-center gap-3 rounded-card bg-tone-primary-bg px-4 py-3 text-foreground"
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-pill bg-primary text-md font-extrabold text-primary-foreground tabular-nums">
                      {reviewCount}
                    </span>
                    <span className="flex-1 text-lg font-bold">
                      {t("reviewShort", { count: reviewCount })}
                    </span>
                    <ChevronRight size={18} aria-hidden="true" />
                  </Link>
                )}
                {summary.excluded_count > 0 && (
                  <Link to="/receipts?status=manual_review" className="text-inherit">
                    <Note tone="warning">
                      <span className="flex items-center justify-between gap-3">
                        <span className="tabular-nums">
                          {t("heldOutPhone", {
                            count: summary.excluded_count,
                            worth: heldOutWorth,
                          })}
                        </span>
                        <ChevronRight size={16} aria-hidden="true" className="shrink-0" />
                      </span>
                    </Note>
                  </Link>
                )}
                {incomeStore.pending.map((pending) => (
                  <PendingIncomeCard
                    key={pending.id}
                    pending={pending}
                    currency={currency}
                    onReview={() => {
                      setReviewing(pending.id);
                    }}
                    onDismiss={() => {
                      void incomeStore.dismissPending(pending.id);
                    }}
                  />
                ))}
                {askPayday && usual !== null && (
                  <PaydayPrompt
                    usual={usual}
                    currency={currency}
                    busy={confirming}
                    onConfirm={() => {
                      setConfirming(true);
                      void incomeStore
                        .receive(
                          { amount: usual, source: t("edit.incomeSource"), kind: "salary" },
                          today,
                          shown,
                        )
                        .finally(() => {
                          setConfirming(false);
                        });
                    }}
                    onOther={() => {
                      setEditing("income");
                    }}
                  />
                )}
                <BalanceCard
                  balance={incomeStore.balance}
                  currency={currency}
                  onEdit={() => {
                    setEditing("balance");
                  }}
                  onAddIncome={() => {
                    setEditing("received");
                  }}
                />
                <MonthTrips trips={budgetStore.trips} currency={currency} />
              </div>
            </div>

            <CategoryTiles
              spend={budgetStore.spend}
              hrefFor={(categoryId) => categoryItemsHref(summary, categoryId)}
            />

            <PriceInsight />

            <RecentPurchases
              title={summary.is_complete ? t("biggest") : t("latest")}
              receipts={budgetStore.receipts}
              total={budgetStore.receiptsInMonth}
              allHref={`/receipts?${monthQuery(summary)}`}
              onOpen={(id) => {
                void receiptStore.fetchReceiptDetail(id);
              }}
            />
          </>
        )}

        {editing === "income" && (
          <AmountDialog
            title={t("edit.incomeTitle", { month: MONTH.format(selected) })}
            label={t("edit.incomeLabel")}
            hint={entries.length > 1 ? t("edit.incomeMany") : t("edit.incomeHint")}
            initial={entries.length === 1 ? (entries[0]?.amount ?? "") : ""}
            currency={currency}
            onSave={(amount) =>
              incomeStore.setMonthTotal(year, month, amount, t("edit.incomeSource"))
            }
            onClose={() => {
              setEditing(null);
            }}
          />
        )}
        {editing === "budget" && (
          <AmountDialog
            title={t("edit.budgetTitle")}
            label={t("edit.budgetLabel")}
            hint={t("edit.budgetHint")}
            initial={summary.budget_limit ?? ""}
            currency={currency}
            allowEmpty
            onSave={async (amount) => {
              const ok = await profileStore.saveQuietly({
                budget_limit: amount === "" ? null : amount,
              });
              if (ok) await budgetStore.refresh();
              return ok;
            }}
            onClose={() => {
              setEditing(null);
            }}
          />
        )}

        {reviewing && (
          <IncomeDialog
            entry={null}
            draft={incomeStore.pending.find((p) => p.id === reviewing) ?? null}
            pendingId={reviewing}
            defaultDay={today}
            onClose={() => {
              setReviewing(null);
            }}
            onSaved={() => {
              void incomeStore.load(year, month);
              void incomeStore.loadBalance(today);
            }}
          />
        )}
        {editing === "received" && (
          <AmountDialog
            title={t("received.title")}
            label={t("received.label")}
            hint={t("received.hint")}
            initial=""
            currency={currency}
            onSave={(amount) =>
              incomeStore.receive(
                { amount, source: t("received.source"), kind: "other" },
                today,
                running ? shown : budgetStore.current,
              )
            }
            onClose={() => {
              setEditing(null);
            }}
          />
        )}
        {editing === "balance" && (
          <AmountDialog
            title={t("balance.editTitle")}
            label={t("balance.editLabel")}
            hint={t("balance.editHint")}
            initial={incomeStore.balance?.balance ?? ""}
            currency={currency}
            onSave={async (amount) => {
              const ok = await profileStore.saveQuietly({
                starting_balance: amount,
                balance_since: today,
              });
              if (ok) await incomeStore.loadBalance(today);
              return ok;
            }}
            onClose={() => {
              setEditing(null);
            }}
          />
        )}

        {receiptStore.selectedReceiptId && <ReceiptDetailModal />}
        <DeleteReceiptDialog />
        <EditReceiptDialog />
      </div>
    </div>
  );
});

/** The figure's month as `start=…&end=…`, how the receipts and categories screens take it. */
function monthQuery(month: { year: number; month: number }): string {
  const { start, end } = monthRange(month);
  return `start=${start}&end=${end}`;
}

/** One category's items in the figure's month, on the categories screen. */
function categoryItemsHref(month: { year: number; month: number }, categoryId: string): string {
  return `/categories?view=all&category=${encodeURIComponent(categoryId)}&${monthQuery(month)}`;
}

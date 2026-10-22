import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus, Target } from "lucide-react";

import {
  BackLink,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Note,
} from "@/shared/components";
import type { Goal } from "@/stores/GoalsStore";
import { useStores } from "@/stores/StoreContext";
import { AtRiskWarnings } from "../components/AtRiskWarnings";
import { GoalAdvice } from "../components/GoalAdvice";
import { GoalCard } from "../components/GoalCard";
import { GoalDialog } from "../components/GoalDialog";
import { useTranslation } from "react-i18next";
import { categoryName } from "@/shared/categoryName";

/**
 * Goals (docs/design/screens/goals.html), first slice: the goals the user has
 * stated, money and lifestyle alike, each editable, and a way to state another
 * (BRD F1 — F8.1), each with its own advice built from the user's receipts (F8.4).
 */
export const GoalsPage = observer(function GoalsPage() {
  const { goalsStore, categoriesStore, authStore, adviceStore } = useStores();
  const { t } = useTranslation("goals");
  const { t: common } = useTranslation();
  const { goals, isLoading, loadError } = goalsStore;
  const currency = authStore.user?.currency ?? "PLN";
  // null: closed; "new": stating a goal; a goal: editing it.
  const [editing, setEditing] = useState<Goal | "new" | null>(null);

  useEffect(() => {
    void goalsStore.load();
    void adviceStore.load();
    categoriesStore.ensureCategories();
  }, [goalsStore, adviceStore, categoriesStore]);

  const nameOf = (id: string | null | undefined) => {
    const name = categoriesStore.categories.find((c) => c.id === id)?.name;
    return name ? categoryName(name) : null;
  };

  const newGoal = (
    <Button
      className="min-h-11 w-full md:min-h-0 md:w-auto"
      onClick={() => {
        setEditing("new");
      }}
    >
      <Plus size={16} aria-hidden="true" />
      {t("newGoal")}
    </Button>
  );

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5.5">
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col items-start gap-2">
            <BackLink to="/plan" label={common("nav.plan")} />
            <h1 className="m-0 text-3xl font-extrabold tracking-[-0.02em]">{t("title")}</h1>
            <p className="m-0 text-lg text-muted-foreground">{t("subtitle")}</p>
          </div>
          {goals.length > 0 && newGoal}
        </header>

        <AtRiskWarnings />

        {adviceStore.loadError && goals.length > 0 && (
          <Note tone="error">
            {t("adviceLoadFailed")} {adviceStore.loadError}
          </Note>
        )}

        {loadError ? (
          <ErrorState layout="banner" title={t("loadFailed")} message={loadError} />
        ) : isLoading && goals.length === 0 ? (
          <LoadingState title={t("loading")} />
        ) : goals.length === 0 ? (
          <Card variant="surface" className="px-5 py-10">
            <EmptyState
              icon={Target}
              iconTone="primary"
              title={t("empty.title")}
              message={t("empty.message")}
              action={newGoal}
            />
          </Card>
        ) : (
          <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-2">
            {goals.map((goal) => (
              <li key={goal.id}>
                <GoalCard
                  goal={goal}
                  currency={currency}
                  categoryName={nameOf}
                  onEdit={() => {
                    setEditing(goal);
                  }}
                  standing={adviceStore.progress.get(goal.id)}
                >
                  <GoalAdvice goal={goal} />
                </GoalCard>
              </li>
            ))}
          </ul>
        )}
      </div>

      {editing && (
        <GoalDialog
          goal={editing === "new" ? null : editing}
          onClose={() => {
            setEditing(null);
          }}
        />
      )}
    </div>
  );
});

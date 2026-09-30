import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus, Target } from "lucide-react";

import { Button, Card, EmptyState, ErrorState, LoadingState, Note } from "@/shared/components";
import type { Goal } from "@/stores/GoalsStore";
import { useStores } from "@/stores/StoreContext";
import { GoalAdvice } from "../components/GoalAdvice";
import { GoalCard } from "../components/GoalCard";
import { GoalDialog } from "../components/GoalDialog";

/**
 * Goals (docs/design/screens/goals.html), first slice: the goals the user has
 * stated, money and lifestyle alike, each editable, and a way to state another
 * (BRD F1 — F8.1), each with its own advice built from the user's receipts (F8.4).
 */
export const GoalsPage = observer(function GoalsPage() {
  const { goalsStore, categoriesStore, authStore, adviceStore } = useStores();
  const { goals, isLoading, loadError } = goalsStore;
  const currency = authStore.user?.currency ?? "PLN";
  // null: closed; "new": stating a goal; a goal: editing it.
  const [editing, setEditing] = useState<Goal | "new" | null>(null);

  useEffect(() => {
    void goalsStore.load();
    void adviceStore.load();
    categoriesStore.ensureCategories();
  }, [goalsStore, adviceStore, categoriesStore]);

  const categoryName = (id: string | null | undefined) =>
    categoriesStore.categories.find((c) => c.id === id)?.name ?? null;

  const newGoal = (
    <Button
      className="min-h-11 w-full md:min-h-0 md:w-auto"
      onClick={() => {
        setEditing("new");
      }}
    >
      <Plus size={16} aria-hidden="true" />
      New goal
    </Button>
  );

  return (
    <div className="flex-grow flex flex-col items-center py-4 md:py-10 md:px-8">
      <div className="w-full max-w-[1000px] flex flex-col gap-4 md:gap-5.5">
        <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[24px] font-bold tracking-[-0.02em] md:text-[28px]">Goals</h1>
            <p className="m-0 text-lg text-muted-foreground">
              Say what you are aiming at, and each goal gets advice built from your own receipts.
            </p>
          </div>
          {goals.length > 0 && newGoal}
        </header>

        {adviceStore.loadError && goals.length > 0 && (
          <Note tone="error">Your advice could not be loaded. {adviceStore.loadError}</Note>
        )}

        {loadError ? (
          <ErrorState layout="banner" title="Your goals could not be loaded" message={loadError} />
        ) : isLoading && goals.length === 0 ? (
          <LoadingState title="Loading your goals…" />
        ) : goals.length === 0 ? (
          <Card variant="surface" className="px-5 py-10">
            <EmptyState
              icon={Target}
              iconTone="primary"
              title="No goals yet"
              message="A spending ceiling, an amount to save, less spent on one category, or a change in how you live — the advice is built around it."
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
                  categoryName={categoryName}
                  onEdit={() => {
                    setEditing(goal);
                  }}
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

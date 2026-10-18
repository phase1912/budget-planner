import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { ChevronDown, Pencil, Plus, Target } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Ring } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import type { Goal } from "@/stores/GoalsStore";
import { useStores } from "@/stores/StoreContext";
import { GoalAdvice } from "@/features/goals/components/GoalAdvice";
import { GoalDialog } from "@/features/goals/components/GoalDialog";
import { goalMeter } from "@/features/goals/goalMeter";

const WHOLE = numberFormat({ maximumFractionDigits: 0 });
const TONE = {
  good: "var(--color-primary)",
  warn: "var(--color-warning)",
  over: "var(--color-error)",
};

/**
 * Goals in Plan (plan.html, F23.13): a ring a goal — how far into its cap, or how much of
 * its saving this month leaves room for — that opens in place to its advice and edit,
 * and a new goal started here, never on another page.
 */
export const PlanGoals = observer(function PlanGoals({
  currency,
  freeThisMonth,
}: {
  currency: string;
  /** What this month leaves free: income after taxes, less bills and spending. */
  freeThisMonth: number | null;
}) {
  const { goalsStore, adviceStore, categoriesStore } = useStores();
  const { t } = useTranslation("plan");
  const [open, setOpen] = useState<string | null>(null);
  const [editing, setEditing] = useState<Goal | "new" | null>(null);

  useEffect(() => {
    void adviceStore.load();
    categoriesStore.ensureCategories();
  }, [adviceStore, categoriesStore]);

  return (
    <>
      {goalsStore.goals.length === 0 ? (
        <p className="m-0 text-md text-muted-foreground">{t("goals.none")}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {goalsStore.goals.map((goal) => {
            const meter = goalMeter(goal, adviceStore.progress.get(goal.id), freeThisMonth);
            const isOpen = open === goal.id;
            return (
              <li key={goal.id} className="overflow-hidden rounded-card control-fill">
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => {
                    setOpen(isOpen ? null : goal.id);
                  }}
                  className="flex min-h-18 w-full items-center gap-3.5 px-3.5 py-3 text-left"
                >
                  {meter ? (
                    <Ring
                      className="h-14 w-14 shrink-0"
                      thickness={0.22}
                      max={100}
                      segments={[{ value: meter.percent, color: TONE[meter.tone] }]}
                      label={t("goals.ring", { percent: Math.round(meter.percent) })}
                    >
                      <span className="text-md font-extrabold tabular-nums">
                        {Math.round(meter.percent)}%
                      </span>
                    </Ring>
                  ) : (
                    <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-pill bg-tone-primary-bg text-primary">
                      <Target size={24} aria-hidden="true" />
                    </span>
                  )}
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="break-words text-lg font-bold">{goal.name}</span>
                    <span className="text-md text-muted-foreground tabular-nums">
                      {meter?.line.kind === "paced"
                        ? t(meter.line.onTrack ? "goals.paced" : "goals.pacedOver", {
                            spent: WHOLE.format(meter.line.spent),
                            target: WHOLE.format(meter.line.target),
                            projected: WHOLE.format(meter.line.projected),
                            currency,
                          })
                        : meter?.line.kind === "saving"
                          ? t("goals.saving", {
                              available: WHOLE.format(meter.line.available),
                              target: WHOLE.format(meter.line.target),
                              currency,
                            })
                          : t(`goals.kinds.${goal.type}`)}
                    </span>
                  </span>
                  <ChevronDown
                    size={18}
                    aria-hidden="true"
                    className={`shrink-0 text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`}
                  />
                </button>
                {isOpen && (
                  // The advice draws its own rule on top: a second one here doubled it.
                  <div className="flex flex-col gap-3 px-3.5 pb-3.5">
                    {goal.description && (
                      <p className="m-0 text-md text-muted-foreground">{goal.description}</p>
                    )}
                    <GoalAdvice goal={goal} />
                    <button
                      type="button"
                      className="flex min-h-11 items-center gap-2 self-start text-md font-bold text-primary"
                      onClick={() => {
                        setEditing(goal);
                      }}
                    >
                      <Pencil size={16} aria-hidden="true" />
                      {t("goals.edit")}
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <button
        type="button"
        className="flex min-h-11 items-center gap-2 self-start text-lg font-bold text-primary"
        onClick={() => {
          setEditing("new");
        }}
      >
        <Plus size={18} aria-hidden="true" />
        {t("goals.new")}
      </button>
      {editing && (
        <GoalDialog
          goal={editing === "new" ? null : editing}
          onClose={() => {
            setEditing(null);
            void adviceStore.loadProgress();
          }}
        />
      )}
    </>
  );
});

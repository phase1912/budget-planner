import { ChevronDown, Lightbulb, Loader2, RefreshCw } from "lucide-react";
import { observer } from "mobx-react-lite";

import { Button, IconTile, Note, Pill } from "@/shared/components";
import type { Goal } from "@/stores/GoalsStore";
import { useStores } from "@/stores/StoreContext";
import { impactOf } from "../adviceImpact";
import { timeAgo } from "../timeAgo";

/**
 * The advice on one goal, inside the goal's card (BRD F3, F4 — F8.4, F8.5).
 *
 * Each recommendation leads with what to do and what that saves; why — the
 * figures from the user's own receipts — opens on demand, so a card with three pieces of advice stays
 * readable. Asking, the wait, and an ask that found nothing or failed all show
 * here, where the button was pressed.
 */
export const GoalAdvice = observer(function GoalAdvice({ goal }: { goal: Goal }) {
  const { adviceStore, authStore } = useStores();
  const currency = authStore.user?.currency ?? "PLN";
  const advice = adviceStore.forGoal(goal.id);
  const outcome = adviceStore.outcomes.get(goal.id);
  const advising = adviceStore.advisingGoalId === goal.id;
  const verb = advice.length > 0 ? "Refresh advice" : "Get advice";

  return (
    <section
      aria-label={`Advice on ${goal.name}`}
      className="flex flex-col gap-3 border-t border-border pt-4"
    >
      <div className="flex items-center gap-2">
        <IconTile tone="accent" size="sm">
          <Lightbulb size={14} aria-hidden="true" />
        </IconTile>
        <h3 className="m-0 text-md font-bold">Advice from your receipts</h3>
      </div>

      <div aria-live="polite" className="flex flex-col gap-2.5">
        {advising && (
          <p className="m-0 inline-flex items-center gap-2 text-md text-muted-foreground">
            <Loader2 size={14} className="animate-spin" aria-hidden="true" />
            Reading your receipts…
          </p>
        )}
        {!advising && outcome && (
          <Note tone={outcome.kind === "failed" ? "error" : "info"}>{outcome.message}</Note>
        )}
        {advice.length > 0 ? (
          <ol className="m-0 flex list-none flex-col gap-2 p-0">
            {advice.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-0.5 rounded-control border border-border bg-surface px-3.5 py-2.5"
              >
                <p className="m-0 text-md font-semibold">{item.action}</p>
                <p className="m-0 text-base font-semibold text-tone-primary-text tabular-nums">
                  {impactOf(item, currency)}
                </p>
                <details className="group">
                  <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-1 text-base font-medium text-muted-foreground transition-colors hover:text-foreground md:min-h-0 md:py-0.5 [&::-webkit-details-marker]:hidden">
                    Why?
                    <ChevronDown
                      size={13}
                      aria-hidden="true"
                      className="transition-transform group-open:rotate-180"
                    />
                  </summary>
                  <div className="flex flex-col items-start gap-1.5 pb-1">
                    <p className="m-0 text-md text-muted-foreground">{item.rationale}</p>
                    <Pill size="sm">{item.target_name}</Pill>
                  </div>
                </details>
              </li>
            ))}
          </ol>
        ) : (
          !advising &&
          !outcome && (
            <p className="m-0 text-md text-muted-foreground">
              Ask and the advice names things you actually buy, not general tips.
            </p>
          )
        )}
      </div>

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <Button
          variant="secondary"
          size="sm"
          className="min-h-11 w-full md:min-h-0 md:w-auto"
          aria-label={`${verb} on ${goal.name}`}
          disabled={adviceStore.advisingGoalId !== null}
          onClick={() => void adviceStore.advise(goal.id)}
        >
          {advice.length > 0 ? (
            <RefreshCw size={14} aria-hidden="true" className={advising ? "animate-spin" : ""} />
          ) : (
            <Lightbulb size={14} aria-hidden="true" />
          )}
          {advising ? "Working it out…" : verb}
        </Button>
        {advice[0] && (
          <span className="text-base text-muted-foreground">
            Updated {timeAgo(advice[0].created_at)}
          </span>
        )}
      </div>
    </section>
  );
});

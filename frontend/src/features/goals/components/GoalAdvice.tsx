import { ChevronDown, Lightbulb, Loader2, RefreshCw } from "lucide-react";
import { observer } from "mobx-react-lite";

import { Button, IconTile, Meter, Note, Pill } from "@/shared/components";
import type { AdviceReadiness } from "@/stores/AdviceStore";
import type { Goal } from "@/stores/GoalsStore";
import { useStores } from "@/stores/StoreContext";
import { impactOf } from "../adviceImpact";
import { timeAgo } from "../timeAgo";

/**
 * The advice on one goal, inside the goal's card (BRD F3, F4 — F8.4, F8.5).
 *
 * Each recommendation leads with what to do and what that saves; why — the
 * figures from the user's own receipts — opens on demand, so a card with three
 * pieces of advice stays readable. Asking, the wait, and an ask that found nothing
 * or failed all show here, where the button was pressed. Until there is enough
 * history (BRD F5), the block says how far there is to go instead of offering to ask.
 */
export const GoalAdvice = observer(function GoalAdvice({ goal }: { goal: Goal }) {
  const { adviceStore, authStore } = useStores();
  const currency = authStore.user?.currency ?? "PLN";
  const advice = adviceStore.forGoal(goal.id);
  const outcome = adviceStore.outcomes.get(goal.id);
  const advising = adviceStore.advisingGoalId === goal.id;
  const readiness = adviceStore.readiness;
  const waiting = readiness !== null && !readiness.ready && advice.length === 0;
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

      {waiting ? (
        <NotEnoughHistory readiness={readiness} />
      ) : (
        <>
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
                <RefreshCw
                  size={14}
                  aria-hidden="true"
                  className={advising ? "animate-spin" : ""}
                />
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
        </>
      )}
    </section>
  );
});

/**
 * Advice before there is enough history to base it on (BRD F5): how far there is to go,
 * stated in words as well as drawn, and no button to ask, since asking would only be
 * refused. It turns into the advice block by itself once the history is there.
 */
function NotEnoughHistory({ readiness }: { readiness: AdviceReadiness }) {
  const fewReceipts = readiness.receipts < readiness.required_receipts;
  const receipts = readiness.receipts === 1 ? "receipt" : "receipts";
  const days = readiness.history_days === 1 ? "day" : "days";
  return (
    <div className="flex flex-col gap-2">
      <p className="m-0 text-md font-semibold">
        {fewReceipts
          ? `${String(readiness.receipts)} ${receipts} is not a pattern yet`
          : `${String(readiness.history_days)} ${days} is not a pattern yet`}
      </p>
      <p className="m-0 text-md text-muted-foreground">
        Advice needs about a month of shopping behind it. Keep uploading and it turns on by itself.
      </p>
      <div className="flex flex-col gap-1.5 md:max-w-60">
        <Meter value={readiness.progress} />
        <span className="text-base text-muted-foreground tabular-nums">
          {readiness.receipts} of {readiness.required_receipts} receipts · {readiness.history_days}{" "}
          of {readiness.required_days} days
        </span>
      </div>
    </div>
  );
}

import { ChevronDown, Lightbulb, Loader2, RefreshCw, Undo2 } from "lucide-react";
import { observer } from "mobx-react-lite";

import { Button, IconTile, Meter, Note, Pill } from "@/shared/components";
import {
  isMonthPace,
  type AdviceReadiness,
  type MonthPace,
  type Recommendation,
} from "@/stores/AdviceStore";
import type { Goal } from "@/stores/GoalsStore";
import { useStores } from "@/stores/StoreContext";
import { impactOf } from "../adviceImpact";
import { timeAgo } from "../timeAgo";
import { watchedLines } from "../watchedLines";
import { categoryName } from "@/shared/categoryName";
import { numberFormat, dateFormat } from "@/i18n/format";
import { useTranslation, Trans } from "react-i18next";
import type { TFunction } from "i18next";

/** What an ask that found nothing read, so "nothing" is checkable (F8.11.3). */
function lookedAt(t: TFunction<"goals">, watched: string[], months: number): string {
  return watched.length > 0
    ? t("advice.lookedAt", { lines: watched.join(", "), count: months })
    : t("advice.lookedAtAll", { count: months });
}

/**
 * The advice on one goal, inside the goal's card (BRD F3, F4 — F8.4, F8.5).
 *
 * Each recommendation leads with what to do and what that saves; why — the
 * figures from the user's own receipts — opens on demand, so a card with three
 * pieces of advice stays readable. Asking, the wait, and an ask that found nothing
 * or failed all show here, where the button was pressed. Until there is enough
 * history (BRD F5), the block says how far there is to go instead of offering to ask;
 * while a monthly money goal is on track, it says there is nothing to cut (F6). Each
 * piece of advice can be marked won't-follow or not helpful (F8.9).
 */
export const GoalAdvice = observer(function GoalAdvice({ goal }: { goal: Goal }) {
  const { adviceStore, authStore, categoriesStore } = useStores();
  const { t } = useTranslation("goals");
  const currency = authStore.user?.currency ?? "PLN";
  const advice = adviceStore.forGoal(goal.id);
  const outcome = adviceStore.outcomes.get(goal.id);
  const advising = adviceStore.advisingGoalId === goal.id;
  const readiness = adviceStore.readiness;
  const waiting = readiness !== null && !readiness.ready && advice.length === 0;
  const standing = adviceStore.progress.get(goal.id);
  const pace = isMonthPace(standing) ? standing : undefined;
  const verb = advice.length > 0 ? t("advice.refresh") : t("advice.get");
  const latest = advice.find((item) => !item.feedback) ?? advice[0];

  return (
    <section
      aria-label={t("advice.section", { name: goal.name })}
      className="flex flex-col gap-3 border-t border-border pt-4"
    >
      <div className="flex items-center gap-2">
        <IconTile tone="accent" size="sm">
          <Lightbulb size={14} aria-hidden="true" />
        </IconTile>
        <h3 className="m-0 text-md font-bold">{t("advice.heading")}</h3>
      </div>

      {waiting ? (
        <NotEnoughHistory readiness={readiness} />
      ) : pace?.on_track ? (
        <NothingToCut pace={pace} currency={currency} />
      ) : (
        <>
          <div aria-live="polite" className="flex flex-col gap-2.5">
            {advising && (
              <p className="m-0 inline-flex items-center gap-2 text-md text-muted-foreground">
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                {t("advice.reading")}
              </p>
            )}
            {!advising && outcome && (
              <Note tone={outcome.kind === "failed" ? "error" : "info"}>
                {outcome.kind === "nothing_specific" && readiness
                  ? lookedAt(
                      t,
                      watchedLines(goal, (id) => {
                        const name = categoriesStore.categories.find((c) => c.id === id)?.name;
                        return name ? categoryName(name) : null;
                      }),
                      readiness.analysis_months,
                    )
                  : outcome.message}
              </Note>
            )}
            {advice.length > 0 ? (
              <ol className="m-0 flex list-none flex-col gap-2 p-0">
                {advice.map((item) => (
                  <li
                    key={item.id}
                    className={`flex flex-col gap-0.5 rounded-control border border-border px-3.5 py-2.5 ${item.feedback ? "bg-muted" : "bg-surface"}`}
                  >
                    <p
                      className={`m-0 text-md font-semibold ${item.feedback ? "text-muted-foreground line-through" : ""}`}
                    >
                      {item.action}
                    </p>
                    <p className="m-0 text-base font-semibold text-tone-primary-text tabular-nums">
                      {impactOf(item, currency)}
                    </p>
                    <details className="group">
                      <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-1 text-base font-medium text-muted-foreground transition-colors hover:text-foreground md:min-h-0 md:py-0.5 [&::-webkit-details-marker]:hidden">
                        {t("advice.why")}
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
                    <FeedbackControls item={item} />
                  </li>
                ))}
              </ol>
            ) : (
              !advising &&
              !outcome && <p className="m-0 text-md text-muted-foreground">{t("advice.prompt")}</p>
            )}
          </div>

          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <Button
              variant="secondary"
              size="sm"
              className="min-h-11 w-full md:min-h-0 md:w-auto"
              aria-label={t("advice.buttonLabel", { verb, name: goal.name })}
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
              {advising ? t("advice.working") : verb}
            </Button>
            {latest && (
              <span className="text-base text-muted-foreground">
                {t("advice.updated", { ago: timeAgo(latest.created_at) })}
              </span>
            )}
          </div>
        </>
      )}
    </section>
  );
});

/**
 * The user's say on one piece of advice (BRD F8 — F8.9): won't follow it, or not helpful.
 * Marked advice stays on the card, struck through with an undo, and the next ask for
 * advice is told not to repeat it.
 */
const FeedbackControls = observer(function FeedbackControls({ item }: { item: Recommendation }) {
  const { adviceStore } = useStores();
  const { t } = useTranslation("goals");
  if (item.feedback) {
    return (
      <div className="flex items-center justify-between gap-2">
        <span className="text-base text-muted-foreground">{t(`feedback.${item.feedback}`)}</span>
        <Button
          variant="ghost"
          size="sm"
          className="min-h-11 md:min-h-0"
          aria-label={t("feedback.undoLabel", { action: item.action })}
          onClick={() => void adviceStore.updateFeedback(item.id, null)}
        >
          <Undo2 size={14} aria-hidden="true" />
          {t("feedback.undo")}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex gap-2">
      <Button
        variant="secondary"
        size="sm"
        className="min-h-11 flex-1 md:min-h-0 md:flex-none"
        aria-label={t("feedback.wontFollowLabel", { action: item.action })}
        onClick={() => void adviceStore.updateFeedback(item.id, "not_followed")}
      >
        {t("feedback.wontFollow")}
      </Button>
      <Button
        variant="secondary"
        size="sm"
        className="min-h-11 flex-1 md:min-h-0 md:flex-none"
        aria-label={t("feedback.notHelpfulLabel", { action: item.action })}
        onClick={() => void adviceStore.updateFeedback(item.id, "not_helpful")}
      >
        {t("feedback.notHelpful")}
      </Button>
    </div>
  );
});

/**
 * Advice before there is enough history to base it on (BRD F5): how far there is to go,
 * stated in words as well as drawn, and no button to ask, since asking would only be
 * refused. It turns into the advice block by itself once the history is there.
 */
function NotEnoughHistory({ readiness }: { readiness: AdviceReadiness }) {
  const { t } = useTranslation("goals");
  const fewReceipts = readiness.receipts < readiness.required_receipts;
  return (
    <div className="flex flex-col gap-2">
      <p className="m-0 text-md font-semibold">
        {fewReceipts
          ? t("history.receipts", { count: readiness.receipts })
          : t("history.days", { count: readiness.history_days })}
      </p>
      <p className="m-0 text-md text-muted-foreground">{t("history.note")}</p>
      <div className="flex flex-col gap-1.5 md:max-w-60">
        <Meter value={readiness.progress} />
        <span className="text-base text-muted-foreground tabular-nums">
          {t("history.progress", {
            receipts: readiness.receipts,
            requiredReceipts: readiness.required_receipts,
            days: readiness.history_days,
            requiredDays: readiness.required_days,
          })}
        </span>
      </div>
    </div>
  );
}

const MONTH = dateFormat({ month: "long" });
const MONEY = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const EARLY_DAYS = 7;

/**
 * A monthly money goal on pace to finish under its cap (BRD F6): progress, not cuts.
 * The figures are worked out live from this month's receipts, so the card never
 * says "on track" after the month has turned.
 */
function NothingToCut({ pace, currency }: { pace: MonthPace; currency: string }) {
  const { t } = useTranslation("goals");
  const month = MONTH.format(new Date());
  const money = (amount: number | string) => `${MONEY.format(Number(amount))} ${currency}`;
  const left = Number(pace.target) - Number(pace.spent);
  return (
    <Note tone="success">
      <div className="flex flex-col gap-1.5">
        <span className="font-semibold">{t("onTrack.heading")}</span>
        <span>
          <Trans
            t={t}
            i18nKey="onTrack.spent"
            values={{ spent: money(pace.spent), target: money(pace.target) }}
            components={{ b: <strong /> }}
          />
          {left > 0 && t("onTrack.left", { left: money(left) })}.
        </span>
        <span>
          <Trans
            t={t}
            i18nKey="onTrack.estimate"
            values={{ month, projected: money(pace.projected), margin: money(pace.margin) }}
            components={{ b: <strong /> }}
          />
        </span>
        {pace.day <= EARLY_DAYS && (
          <span className="opacity-80">
            {t("onTrack.early", { day: pace.day, days: pace.days_in_month })}
          </span>
        )}
      </div>
    </Note>
  );
}

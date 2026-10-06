import { useEffect } from "react";
import { X } from "lucide-react";
import { observer } from "mobx-react-lite";
import { Link } from "react-router-dom";

import { IconButton, Note } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

const MONTH = new Intl.DateTimeFormat("en-GB", { month: "long" });
const MONEY = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Goals heading over their cap this month, waiting for the user without their asking
 * (BRD F7 — F8.8). Each says how far over the month is heading and where the advice
 * to correct course is: the background pass has already prepared it. Set aside, a
 * warning stays away until next month. Shown on the dashboard and on Goals.
 */
export const AtRiskWarnings = observer(function AtRiskWarnings({
  linkToGoals = false,
}: {
  /** Point to the Goals screen for the advice; off when already on it. */
  linkToGoals?: boolean;
}) {
  const { adviceStore, authStore } = useStores();
  const currency = authStore.user?.currency ?? "PLN";
  const money = (amount: string | number) => `${MONEY.format(Number(amount))} ${currency}`;
  const month = MONTH.format(new Date());

  useEffect(() => {
    void adviceStore.loadProgress();
  }, [adviceStore]);

  if (adviceStore.warnings.length === 0) return null;

  return (
    <ul aria-label="Goals at risk" className="m-0 flex list-none flex-col gap-3 p-0">
      {adviceStore.warnings.map((pace) => (
        <li key={pace.goal_id}>
          <Note tone="warning">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 flex-col gap-1">
                <span className="font-semibold">{pace.goal_name} is heading over its limit</span>
                <span>
                  Spent so far: {money(pace.spent)} of {money(pace.target)}. Estimate: at this pace{" "}
                  {month} would end at about <strong>{money(pace.projected)}</strong>,{" "}
                  {money(-Number(pace.margin))} over your limit.
                </span>
                {linkToGoals ? (
                  <Link to="/goals" className="font-semibold text-inherit underline">
                    See how to cut back
                  </Link>
                ) : (
                  <span>Advice to cut back is in the goal&apos;s card below.</span>
                )}
              </div>
              <IconButton
                aria-label={`Set aside the warning for ${pace.goal_name} until next month`}
                className="h-11 w-11 shrink-0 md:h-auto md:w-auto"
                onClick={() => void adviceStore.dismissWarning(pace.goal_id)}
              >
                <X size={16} aria-hidden="true" />
              </IconButton>
            </div>
          </Note>
        </li>
      ))}
    </ul>
  );
});

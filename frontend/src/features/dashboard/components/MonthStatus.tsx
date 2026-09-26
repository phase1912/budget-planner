import { CircleCheck, Clock } from "lucide-react";

import { Pill } from "@/shared/components";

interface MonthStatusProps {
  isComplete: boolean;
}

/**
 * Whether the month on screen is over (BRD D4, D5 — F6.3).
 *
 * "Month-to-date · still running" on an unfinished month, so a partial figure is
 * never taken for a whole one; "Finalised · complete month" once it has ended.
 * Mirrors docs/design/screens/dashboard.html and dashboard-dark.html.
 */
export function MonthStatus({ isComplete }: MonthStatusProps) {
  return isComplete ? (
    <Pill>
      <CircleCheck size={14} aria-hidden="true" />
      Finalised · complete month
    </Pill>
  ) : (
    <Pill tone="info">
      <Clock size={14} aria-hidden="true" />
      Month-to-date · still running
    </Pill>
  );
}

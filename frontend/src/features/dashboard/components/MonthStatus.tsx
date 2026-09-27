import { CircleCheck, Clock } from "lucide-react";

import { Pill } from "@/shared/components";

interface MonthStatusProps {
  isComplete: boolean;
  /** The phone's short form under the month name (dashboard-mobile.html). */
  compact?: boolean;
}

/**
 * Whether the month on screen is over (BRD D4, D5 — F6.3).
 *
 * "Month-to-date · still running" on an unfinished month, so a partial figure is
 * never taken for a whole one; "Finalised · complete month" once it has ended.
 * Mirrors docs/design/screens/dashboard.html and dashboard-dark.html; the
 * compact form reads "Still running" or "Finalised", as on a phone.
 */
export function MonthStatus({ isComplete, compact = false }: MonthStatusProps) {
  const size = compact ? "sm" : "default";
  return isComplete ? (
    <Pill size={size}>
      <CircleCheck size={compact ? 12 : 14} aria-hidden="true" />
      {compact ? "Finalised" : "Finalised · complete month"}
    </Pill>
  ) : (
    <Pill tone="info" size={size}>
      <Clock size={compact ? 12 : 14} aria-hidden="true" />
      {compact ? "Still running" : "Month-to-date · still running"}
    </Pill>
  );
}

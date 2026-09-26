import type { ReactNode } from "react";

import { Meter } from "@/shared/components";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

interface LimitStatusProps {
  limit: string;
  /** The server's share of the limit spent, rounded down; may pass 100. */
  percent: number;
  /** What is left of the limit, negative by the amount over it. */
  remaining: string;
  currency: string;
  /** The line beneath the bar: the month's days and receipts. */
  children?: ReactNode;
}

/**
 * The month's spend as a share of the user's limit (BRD D7 — F6.6), as in
 * docs/design/screens/dashboard.html and, over the limit, dashboard-dark.html.
 *
 * Over the limit the figure is not clamped at 100%: it reads in the error tone,
 * says by how much, and the full bar is notched where the limit sat.
 */
export function LimitStatus({ limit, percent, remaining, currency, children }: LimitStatusProps) {
  const left = Number(remaining);
  const over = left < 0;
  const tone = over ? "text-error" : "text-primary";
  // Past the limit the bar is the whole spend, so the limit sits limit/spend along it.
  const mark = over ? (Number(limit) / (Number(limit) - left)) * 100 : undefined;
  return (
    <div className="mt-1.5 flex flex-col gap-1.75">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
        <span className={`tabular-nums text-md font-semibold ${tone}`}>
          {percent}% of your {AMOUNT.format(Number(limit))} {currency} limit
        </span>
        <span
          className={`tabular-nums text-md ${over ? "font-semibold text-error" : "text-muted-foreground"}`}
        >
          {over
            ? `Over by ${AMOUNT.format(-left)} ${currency}`
            : `${AMOUNT.format(left)} ${currency} left`}
        </span>
      </div>
      <Meter value={over ? 100 : percent} tone={over ? "error" : "primary"} mark={mark} />
      {children}
    </div>
  );
}

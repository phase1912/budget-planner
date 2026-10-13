import type { ReactNode } from "react";

import { Meter } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import { useTranslation } from "react-i18next";

const AMOUNT = numberFormat({
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
  /** Whose limit it is: the user's own, or the household's (F12.5). */
  household?: boolean;
  /** The line beneath the bar: the month's days and receipts. */
  children?: ReactNode;
}

/**
 * The month's spend as a share of the user's limit (BRD D7 — F6.6), as in
 * docs/design/screens/dashboard.html and, over the limit, dashboard-dark.html.
 *
 * Over the limit the figure is not clamped at 100%: it reads in the error tone,
 * says by how much, and the full bar is notched where the limit sat. A phone
 * puts the bar first and drops the currency and "your … limit" from the text
 * (dashboard-mobile.html).
 */
export function LimitStatus({
  limit,
  percent,
  remaining,
  currency,
  household = false,
  children,
}: LimitStatusProps) {
  const { t } = useTranslation("dashboard");
  const left = Number(remaining);
  const over = left < 0;
  const tone = over ? "text-error" : "text-primary";
  // Past the limit the bar is the whole spend, so the limit sits limit/spend along it.
  const mark = over ? (Number(limit) / (Number(limit) - left)) * 100 : undefined;
  const amount = AMOUNT.format(Number(limit));
  const gap = AMOUNT.format(Math.abs(left));
  // A phone shows the short form and drops the currency (dashboard-mobile.html).
  const either = (phone: string, wider: string, className = "") => (
    <>
      <span className={`md:hidden ${className}`}>{phone}</span>
      <span className={`hidden md:inline ${className}`}>{wider}</span>
    </>
  );
  return (
    <div className="flex flex-col gap-1.75 md:mt-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
        <span className={`tabular-nums text-base font-semibold md:text-md ${tone}`}>
          {either(
            t("limit.of", { percent, limit: amount }),
            t(household ? "limit.ofHousehold" : "limit.ofYours", {
              percent,
              limit: amount,
              currency,
            }),
            tone,
          )}
        </span>
        <span
          className={`tabular-nums text-base md:text-md ${over ? "font-semibold text-error" : "text-muted-foreground"}`}
        >
          {over
            ? either(
                t("limit.over", { amount: gap }),
                t("limit.overWide", { amount: gap, currency }),
                "text-error",
              )
            : either(
                t("limit.left", { amount: gap }),
                t("limit.leftWide", { amount: gap, currency }),
              )}
        </span>
      </div>
      {/* A phone draws the bar above the figures (dashboard-mobile.html). */}
      <div className="-order-1 md:order-none">
        <Meter value={over ? 100 : percent} tone={over ? "error" : "primary"} mark={mark} />
      </div>
      {children}
    </div>
  );
}

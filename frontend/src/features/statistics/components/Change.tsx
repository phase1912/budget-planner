import { TrendingDown, TrendingUp } from "lucide-react";

const AMOUNT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});
const PERCENT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

interface ChangeProps {
  /** This period less the previous one. */
  change: string;
  /** The change as a percentage of the previous total; null when the category is new. */
  percent: string | null | undefined;
}

/**
 * A category's change against the previous period (BRD E3), as
 * docs/design/screens/statistics.html prints it: "−69.80 · −8.6%".
 *
 * Spending less reads in the primary tone and spending more in the error tone,
 * since it is spending being measured. A category new this period has no
 * percentage to show and says "new" instead.
 */
export function Change({ change, percent }: ChangeProps) {
  const amount = Number(change);
  if (amount === 0) return <span className="text-muted-foreground">no change</span>;
  const up = amount > 0;
  const Arrow = up ? TrendingUp : TrendingDown;
  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold tabular-nums ${up ? "text-error" : "text-primary"}`}
    >
      <Arrow size={14} aria-hidden="true" className="shrink-0" />
      {AMOUNT.format(amount).replace("-", "−")} ·{" "}
      {percent == null ? "new" : `${PERCENT.format(Number(percent)).replace("-", "−")}%`}
    </span>
  );
}

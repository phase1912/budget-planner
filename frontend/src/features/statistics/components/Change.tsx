import { TrendingDown, TrendingUp } from "lucide-react";
import { numberFormat } from "@/i18n/format";
import i18n from "@/i18n";

const AMOUNT = numberFormat({
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});
const PERCENT = numberFormat({
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

interface ChangeProps {
  /** This period less the previous one. */
  change: string;
  /** The change as a percentage of the previous total; null when the category is new. */
  percent: string | null | undefined;
  /** Only the percentage (or "new"), for a phone's narrow amount cell. */
  compact?: boolean;
}

/**
 * A category's change against the previous period (BRD E3), as
 * docs/design/screens/statistics.html prints it: "−69.80 · −8.6%".
 *
 * Spending less reads in the primary tone and spending more in the error tone,
 * since it is spending being measured. A category new this period has no
 * percentage to show and says "new" instead. The compact form, for a phone,
 * keeps only the percentage; the amount stays in the table.
 */
export function Change({ change, percent, compact = false }: ChangeProps) {
  const amount = Number(change);
  if (amount === 0)
    return <span className="text-muted-foreground">{i18n.t("statistics:noChange")}</span>;
  const up = amount > 0;
  const Arrow = up ? TrendingUp : TrendingDown;
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap font-semibold tabular-nums ${up ? "text-error" : "text-primary"}`}
    >
      <Arrow size={14} aria-hidden="true" className="shrink-0" />
      {!compact && `${AMOUNT.format(amount).replace("-", "−")} · `}
      {percent == null
        ? i18n.t("statistics:new")
        : `${PERCENT.format(Number(percent)).replace("-", "−")}%`}
    </span>
  );
}

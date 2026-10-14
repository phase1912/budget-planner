import { useTranslation } from "react-i18next";

import { Meter } from "@/shared/components";
import { dateFormat, formatAmount } from "@/i18n/format";
import type { Exploration } from "@/stores/ExplorationStore";

const MONTH = dateFormat({ month: "short", year: "numeric" });

/**
 * What the selection cost month by month (F16.2): one bar per month, its amount and how
 * many times it was bought written beside it, so the figure never rests on the bar alone.
 */
export function MonthBars({
  months,
  currency,
}: {
  months: Exploration["months"];
  currency: string;
}) {
  const { t } = useTranslation("products");
  const top = Math.max(...months.map((m) => Number(m.amounts.spent)), 0);
  return (
    <ul aria-label={t("explore.byMonth")} className="m-0 flex list-none flex-col gap-2.5 p-0">
      {months.map((month) => (
        <li
          key={month.month}
          className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 md:grid-cols-[7rem_minmax(0,1fr)_11rem]"
        >
          <span className="text-base text-muted-foreground">
            {MONTH.format(new Date(`${month.month}T00:00:00`))}
          </span>
          <span className="order-3 col-span-2 md:order-none md:col-span-1">
            <Meter value={top > 0 ? (Number(month.amounts.spent) / top) * 100 : 0} />
          </span>
          <span className="text-right text-base tabular-nums text-muted-foreground">
            {month.amounts.times > 0
              ? `${formatAmount(month.amounts.spent)} ${currency} · ${t("explore.times", { count: month.amounts.times })}`
              : t("explore.none")}
          </span>
        </li>
      ))}
    </ul>
  );
}

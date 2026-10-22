import { useTranslation } from "react-i18next";

import { Meter } from "@/shared/components";
import { dateFormat, numberFormat } from "@/i18n/format";
import { isMonthPace, type GoalProgress } from "@/stores/AdviceStore";

const MONEY = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });
const DAY = dateFormat({ day: "numeric", month: "long", year: "numeric" });

/**
 * Where a goal stands, at the top of its card (F8.11.2): a monthly cap's month as a bar,
 * spent against the cap with where it is heading; a savings goal's money saved against its
 * target, by its date, and what is needed a month to make it; a lifestyle goal's watched
 * lines this month against the months before. Every figure is said in words too; the bar
 * only draws it.
 */
export function GoalStanding({
  standing,
  currency,
}: {
  standing: GoalProgress | undefined;
  currency: string;
}) {
  const { t } = useTranslation("goals");
  if (!standing) return null;
  const money = (value: string | number | null | undefined) =>
    `${MONEY.format(Number(value ?? 0))} ${currency}`;

  if (isMonthPace(standing)) {
    const share = (Number(standing.spent) / Math.max(Number(standing.target), 1)) * 100;
    return (
      <div className="flex flex-col gap-1.5">
        <p className="m-0 text-md font-semibold tabular-nums">
          {t("standing.month", { spent: money(standing.spent), target: money(standing.target) })}
        </p>
        <Meter
          value={share}
          tone={Number(standing.spent) > Number(standing.target) ? "error" : "primary"}
        />
        <p
          className={`m-0 text-base ${standing.on_track ? "text-muted-foreground" : "text-tone-error-text"}`}
        >
          {standing.on_track
            ? t("standing.onTrack", { projected: money(standing.projected) })
            : t("standing.over", { projected: money(standing.projected) })}
        </p>
      </div>
    );
  }

  if (standing.kind === "savings") {
    const date = standing.target_date
      ? DAY.format(new Date(`${standing.target_date}T00:00:00`))
      : null;
    return (
      <div className="flex flex-col gap-1.5">
        <p className="m-0 text-md font-semibold tabular-nums">
          {t("standing.saved", {
            saved: money(standing.saved),
            target: money(standing.target),
            percent: standing.percent ?? 0,
          })}
        </p>
        <Meter value={standing.percent ?? 0} />
        <p
          className={`m-0 text-base ${standing.overdue ? "text-tone-error-text" : "text-muted-foreground"}`}
        >
          {standing.reached
            ? t("standing.reached")
            : standing.overdue
              ? t("standing.overdue", {
                  date,
                  left: money(Number(standing.target) - Number(standing.saved)),
                })
              : standing.needed_per_month && date
                ? t("standing.needed", { amount: money(standing.needed_per_month), date })
                : t("standing.noDate")}
        </p>
      </div>
    );
  }

  const change = standing.change_percent;
  return (
    <div className="flex flex-col gap-1">
      <p className="m-0 text-md font-semibold tabular-nums">
        {t("standing.lifestyle", { amount: money(standing.this_month) })}
      </p>
      <p className="m-0 text-base text-muted-foreground">
        {change === null || change === undefined
          ? t("standing.noBefore")
          : change > 0
            ? t("standing.more", { percent: change, usual: money(standing.monthly_average) })
            : t("standing.less", { percent: -change, usual: money(standing.monthly_average) })}
      </p>
    </div>
  );
}

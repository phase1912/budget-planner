import { dateFormat } from "@/i18n/format";
import i18n from "@/i18n";
const DAY = dateFormat({ day: "numeric" });
const DAY_MONTH = dateFormat({ day: "numeric", month: "short" });
const DAY_MONTH_YEAR = dateFormat({
  day: "numeric",
  month: "short",
  year: "numeric",
});

/** A YYYY-MM-DD day as a local date, so formatting never shifts it by the timezone. */
function localDay(iso: string): Date {
  const [year = 0, month = 1, day = 1] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** "1 – 27 Sept 2026", or "28 Aug – 3 Sept 2026" across a month (statistics.html). */
export function periodLabel(start: string, end: string): string {
  const from = localDay(start);
  const to = localDay(end);
  const sameMonth = from.getFullYear() === to.getFullYear() && from.getMonth() === to.getMonth();
  const first = sameMonth
    ? DAY.format(from)
    : from.getFullYear() === to.getFullYear()
      ? DAY_MONTH.format(from)
      : DAY_MONTH_YEAR.format(from);
  return `${first} – ${DAY_MONTH_YEAR.format(to)}`;
}

const MONTH = dateFormat({ month: "long" });

/**
 * The note a comparison stopping partway through a month carries (BRD D4, E3):
 * one running month reads as statistics.html does ("July is still running, so it
 * is compared against the same 27 days of June rather than the whole month");
 * a longer range names both periods.
 */
export function likeForLikeNote(
  current: { start: string; end: string },
  previous: { start: string; end: string },
): string {
  const from = localDay(current.start);
  const to = localDay(current.end);
  if (from.getFullYear() === to.getFullYear() && from.getMonth() === to.getMonth()) {
    const days = to.getDate();
    return i18n.t("statistics:likeForLike.month", {
      count: days,
      month: MONTH.format(to),
      previous: MONTH.format(localDay(previous.start)),
    });
  }
  return i18n.t("statistics:likeForLike.range", {
    current: periodLabel(current.start, current.end),
    previous: periodLabel(previous.start, previous.end),
  });
}

const MONTH_YEAR = dateFormat({ month: "long", year: "numeric" });

/**
 * A period as a phrase to name it by: "March 2025" for one whole calendar month,
 * as the E5 panel in docs/design/screens/states.html reads, else its days.
 */
export function periodName(start: string, end: string): string {
  const from = localDay(start);
  const to = localDay(end);
  const lastDay = new Date(to.getFullYear(), to.getMonth() + 1, 0).getDate();
  const wholeMonth =
    from.getDate() === 1 &&
    to.getDate() === lastDay &&
    from.getFullYear() === to.getFullYear() &&
    from.getMonth() === to.getMonth();
  return wholeMonth ? MONTH_YEAR.format(from) : periodLabel(start, end);
}

import { useTranslation } from "react-i18next";

import { dateFormat } from "@/i18n/format";

const WEEKDAY = dateFormat({ weekday: "long" });
// 5 January 2026 is a Monday: the week from it names the days in the user's language.
const WEEKDAYS = Array.from({ length: 7 }, (_, i) => new Date(2026, 0, 5 + i));

export interface Repeat {
  /** Day of the month, 31 being its last; null: any day. Monthly only. */
  day: number | null;
  /** 0 Monday … 6 Sunday when it repeats weekly (F23.21); null: monthly. */
  weekday: number | null;
}

/** A weekday's name, Monday being 0, in the user's language. */
export function weekdayName(weekday: number): string {
  return WEEKDAY.format(WEEKDAYS[weekday] ?? new Date(2026, 0, 5));
}

/** How often it comes, as a row says it: "on day 10", "every Monday" (F23.21). */
export function useRepeatLabel(): (value: Repeat) => string {
  const { t } = useTranslation();
  return (value) =>
    value.weekday !== null
      ? t("repeat.every", { weekday: weekdayName(value.weekday) })
      : value.day === null
        ? t("repeat.everyMonth")
        : value.day === 31
          ? t("repeat.onLastDay")
          : t("repeat.onDay", { day: value.day });
}

/**
 * What a rule comes to in the month holding `day`: a weekly one as often as its weekday
 * falls in that month, a monthly one once (F23.21) — as the server counts a month.
 */
export function inMonth(amount: string, repeat: Repeat, day: Date): number {
  if (repeat.weekday === null) return Number(amount);
  const last = new Date(day.getFullYear(), day.getMonth() + 1, 0).getDate();
  let times = 0;
  for (let d = 1; d <= last; d++) {
    // getDay() counts from Sunday; the rule counts from Monday.
    if ((new Date(day.getFullYear(), day.getMonth(), d).getDay() + 6) % 7 === repeat.weekday) {
      times++;
    }
  }
  return Number(amount) * times;
}

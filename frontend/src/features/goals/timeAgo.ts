import i18n from "@/i18n";
import { currentLocale } from "@/i18n/format";

const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/** How long ago `iso` was, in words: "just now", "5 minutes ago", "yesterday". */
export function timeAgo(iso: string, now: number = Date.now()): string {
  const seconds = Math.round((now - new Date(iso).getTime()) / 1000);
  for (const [unit, size] of STEPS) {
    if (seconds >= size)
      return new Intl.RelativeTimeFormat(currentLocale(), { numeric: "auto" }).format(
        -Math.floor(seconds / size),
        unit,
      );
  }
  return i18n.t("goals:advice.justNow");
}

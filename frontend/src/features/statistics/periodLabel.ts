const DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric" });
const DAY_MONTH = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });
const DAY_MONTH_YEAR = new Intl.DateTimeFormat("en-GB", {
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

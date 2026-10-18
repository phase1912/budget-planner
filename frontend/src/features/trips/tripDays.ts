/** Where today falls in a trip (holiday.html's "Day 5 of 12"). */
export type TripMoment =
  | { kind: "before"; inDays: number }
  | { kind: "during"; day: number; of: number; left: number }
  | { kind: "after" };

const DAY_MS = 86_400_000;
const at = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));

/**
 * Today against a trip's first and last day, both included: days to go, which day of how
 * many — with the days left counting today — or over. All dates are YYYY-MM-DD.
 */
export function tripMoment(start: string, end: string, today: string): TripMoment {
  const [s, e, d] = [at(start), at(end), at(today)];
  if (d < s) return { kind: "before", inDays: Math.round((s - d) / DAY_MS) };
  if (d > e) return { kind: "after" };
  const of = Math.round((e - s) / DAY_MS) + 1;
  const day = Math.round((d - s) / DAY_MS) + 1;
  return { kind: "during", day, of, left: of - day + 1 };
}

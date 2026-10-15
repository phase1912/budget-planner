/** A time as a `datetime-local` field shows it: the user's own clock, to the minute. */
export function toLocalInput(iso: string): string {
  const at = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${String(at.getFullYear())}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** A `datetime-local` value, read on the user's clock, as an instant the server can count. */
export function fromLocalInput(value: string): string {
  return new Date(value).toISOString();
}

/**
 * How many 24-hour days a stretch from `from` to `to` touches, as the per diem counts them
 * (F20.4): one for anything up to a day, then one more for each started 24 hours.
 */
export function dayCount(from: string, to: string): number {
  const hours = (new Date(to).getTime() - new Date(from).getTime()) / 3_600_000;
  if (!(hours > 0)) return 0;
  return Math.max(1, Math.ceil(hours / 24));
}

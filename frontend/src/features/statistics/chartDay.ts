/** A day on a spending chart: its date and what it came to. */
export interface Day {
  day: string;
  total: string;
}

/** A chart's YYYY-MM-DD as a local date, so the day shown is the day meant. */
export const asDate = (day: string) => new Date(`${day}T00:00:00`);

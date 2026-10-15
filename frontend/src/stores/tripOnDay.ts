import type { Trip } from "@/stores/TripsStore";

/** The trip whose dates hold `day` ("2026-10-03"), or null: one user's trips never overlap. */
export function tripOnDay(trips: Trip[], day: string): Trip | null {
  return trips.find((trip) => trip.start_date <= day && day <= trip.end_date) ?? null;
}

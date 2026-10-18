import { describe, expect, it } from "vitest";

import { tripMoment } from "./tripDays";

describe("tripMoment", () => {
  it("counts the day of the trip and the days left, today included", () => {
    expect(tripMoment("2026-06-03", "2026-06-14", "2026-06-07")).toEqual({
      kind: "during",
      day: 5,
      of: 12,
      left: 8,
    });
  });

  it("says how far off a trip is, and when it is over", () => {
    expect(tripMoment("2026-06-03", "2026-06-14", "2026-05-30")).toEqual({
      kind: "before",
      inDays: 4,
    });
    expect(tripMoment("2026-06-03", "2026-06-14", "2026-06-15")).toEqual({ kind: "after" });
  });
});

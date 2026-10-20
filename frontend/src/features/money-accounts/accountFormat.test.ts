import { describe, expect, it } from "vitest";

import { firstRun, typedAmount } from "./accountFormat";

describe("monthly rules (F23.15)", () => {
  const on18th = new Date(2026, 9, 18);

  it("start next month when their day has already passed", () => {
    expect(firstRun(5, on18th)).toEqual({ date: new Date(2026, 10, 5), nextMonth: true });
  });

  it("start this month on a day still to come, today included", () => {
    expect(firstRun(20, on18th)).toEqual({ date: new Date(2026, 9, 20), nextMonth: false });
    expect(firstRun(18, on18th).nextMonth).toBe(false);
  });

  it("treat the 31st as a short month's last day", () => {
    expect(firstRun(31, new Date(2026, 1, 27))).toEqual({
      date: new Date(2026, 1, 28),
      nextMonth: false,
    });
  });
});

describe("typed amounts", () => {
  it("read spaces and a comma as people type them", () => {
    expect(typedAmount("1 600,50")).toBe("1600.50");
    expect(typedAmount("12abc")).toBeNull();
  });
});

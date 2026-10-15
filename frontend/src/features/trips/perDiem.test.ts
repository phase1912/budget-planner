import { describe, expect, it } from "vitest";

import { dayCount, fromLocalInput, toLocalInput } from "./perDiem";

describe("per diem times (F20.4)", () => {
  it("counts the 24-hour days a stretch touches, as the regulation counts them", () => {
    expect(dayCount("2026-10-13T06:00", "2026-10-13T10:00")).toBe(1);
    expect(dayCount("2026-10-13T06:00", "2026-10-14T06:00")).toBe(1);
    expect(dayCount("2026-10-13T06:00", "2026-10-15T21:00")).toBe(3);
    expect(dayCount("2026-10-14T06:00", "2026-10-13T06:00")).toBe(0);
  });

  it("reads a field's time on the user's clock and shows it back the same", () => {
    expect(toLocalInput(fromLocalInput("2026-10-13T06:30"))).toBe("2026-10-13T06:30");
  });
});

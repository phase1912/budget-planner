import { describe, expect, it } from "vitest";

import { periodLabel } from "./periodLabel";

describe("periodLabel", () => {
  it("names the month once for days within it", () => {
    expect(periodLabel("2026-07-01", "2026-07-27")).toBe("1 – 27 Jul 2026");
  });

  it("names both months across a month boundary, and both years across a year", () => {
    expect(periodLabel("2026-08-28", "2026-09-03")).toBe("28 Aug – 3 Sept 2026");
    expect(periodLabel("2025-12-20", "2026-01-05")).toBe("20 Dec 2025 – 5 Jan 2026");
  });
});

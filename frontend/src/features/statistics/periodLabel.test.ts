import { describe, expect, it } from "vitest";

import { likeForLikeNote, periodLabel } from "./periodLabel";

describe("periodLabel", () => {
  it("names the month once for days within it", () => {
    expect(periodLabel("2026-07-01", "2026-07-27")).toBe("1 – 27 Jul 2026");
  });

  it("names both months across a month boundary, and both years across a year", () => {
    expect(periodLabel("2026-08-28", "2026-09-03")).toBe("28 Aug – 3 Sept 2026");
    expect(periodLabel("2025-12-20", "2026-01-05")).toBe("20 Dec 2025 – 5 Jan 2026");
  });
});

describe("likeForLikeNote", () => {
  it("says a running month is compared against the same days, as the design does", () => {
    expect(
      likeForLikeNote(
        { start: "2026-07-01", end: "2026-07-27" },
        { start: "2026-06-01", end: "2026-06-27" },
      ),
    ).toBe(
      "July is still running, so it is compared against the same 27 days of June rather than the whole month.",
    );
  });

  it("names both periods when the range spans months", () => {
    expect(
      likeForLikeNote(
        { start: "2026-07-01", end: "2026-09-27" },
        { start: "2026-04-01", end: "2026-06-27" },
      ),
    ).toBe(
      "1 Jul – 27 Sept 2026 stops partway through a month, so it is compared against 1 Apr – 27 Jun 2026 rather than whole months.",
    );
  });
});

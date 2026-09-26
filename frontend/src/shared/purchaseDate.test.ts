import { describe, expect, it } from "vitest";

import { formatPurchase, purchaseMonth } from "./purchaseDate";

describe("purchase dates", () => {
  it("shows the time printed on the receipt, not shifted into the browser's timezone", () => {
    expect(formatPurchase("2026-08-04T11:26:00Z", { hour: "2-digit", minute: "2-digit" })).toBe(
      "11:26",
    );
  });

  it("keeps a purchase just before midnight on its own day and month", () => {
    const lastMinute = "2026-08-31T23:30:00Z";
    expect(formatPurchase(lastMinute, { day: "numeric", month: "short" })).toBe("31 Aug");
    expect(purchaseMonth(lastMinute)).toEqual({ year: 2026, month: 8 });
  });
});

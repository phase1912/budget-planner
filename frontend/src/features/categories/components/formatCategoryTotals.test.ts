import { describe, expect, it } from "vitest";

import { formatCategoryTotals, formatItemCount } from "./formatCategoryTotals";

describe("formatCategoryTotals", () => {
  it("says 1 item, not 1 items", () => {
    expect(formatItemCount(1)).toBe("1 item");
    expect(formatItemCount(0)).toBe("0 items");
  });

  it("prints the amount with two decimals and a thousands separator", () => {
    expect(
      formatCategoryTotals({
        id: "x",
        name: "Groceries",
        is_builtin: true,
        item_count: 312,
        total_amount: "1214.6",
      }),
    ).toBe("312 items · 1,214.60 PLN");
  });
});

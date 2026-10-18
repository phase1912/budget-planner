import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CategoryStatistics } from "@/stores/StatisticsStore";
import { SpendingRing } from "./SpendingRing";

const STATS = {
  start: "2026-10-01",
  end: "2026-10-17",
  receipt_count: 5,
  total: "1000.00",
  item_count: 9,
  excluded_count: 0,
  excluded_amount: "0",
  categories: [
    { category_id: "g", name: "Groceries", total: "700.00", share: "70", item_count: 6 },
    {
      category_id: "d",
      name: "Dining",
      total: "300.00",
      share: "30",
      item_count: 3,
      change: "50.00",
      change_percent: "20",
    },
  ],
} as CategoryStatistics;

describe("SpendingRing (F23.4)", () => {
  it("shows the whole, then one category's amount and share when it is tapped", () => {
    render(<SpendingRing statistics={STATS} currency="PLN" />);
    expect(screen.getByText("1,000")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Dining/ }));
    expect(screen.getByRole("button", { name: /Dining/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByText("300").length).toBeGreaterThan(1);

    fireEvent.click(screen.getByRole("button", { name: "Show every category" }));
    expect(screen.getByText("1,000")).toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DailyBars } from "./DailyBars";

const daily = {
  days: [
    { day: "2026-10-01", total: "120.00" },
    { day: "2026-10-02", total: "0" },
    { day: "2026-10-03", total: "64.00" },
    { day: "2026-10-04", total: "0" },
  ],
  total: "184.00",
  average: "61.33",
};

describe("DailyBars", () => {
  it("opens on the latest day with spending and names a day when its bar is tapped", () => {
    render(<DailyBars daily={daily} currency="PLN" today="2026-10-04" />);

    expect(screen.getByText("3 Oct · 64 PLN")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "3 October, 64 PLN" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.click(screen.getByRole("button", { name: "1 October, 120 PLN" }));
    expect(screen.getByText("1 Oct · 120 PLN")).toBeInTheDocument();
    expect(screen.getByText("61 PLN a day on average")).toBeInTheDocument();
  });

  it("lists a bar for every day, quiet ones included", () => {
    render(<DailyBars daily={daily} currency="PLN" today="2026-10-04" />);

    expect(screen.getAllByRole("button")).toHaveLength(4);
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { components } from "@/api/schema";
import { CategoryChart } from "./CategoryChart";

type Chart = components["schemas"]["ChartResponse"];

const GROCERIES: Chart["groups"][number] = {
  category_id: "g",
  name: "Groceries",
  current: { value: "742.60", height: "74.3" },
  previous: { value: "812.40", height: "81.2" },
};

const COMPARED: Chart = {
  scale_max: "1000",
  ticks: ["0", "250", "500", "750", "1000"],
  groups: [GROCERIES],
  hidden: 2,
};

describe("CategoryChart", () => {
  it("draws the bars at the heights the server worked out", () => {
    render(<CategoryChart chart={COMPARED} current="1 – 27 Jul 2026" previous="1 – 27 Jun 2026" />);
    const group = screen.getByRole("img", {
      name: "Groceries, 1 – 27 Jul 2026: 742.60; 1 – 27 Jun 2026: 812.40",
    });
    const heights = Array.from(group.children)
      .slice(0, 2)
      .map((bar) => (bar as HTMLElement).style.height);
    expect(heights).toEqual(["81.2%", "74.3%"]);
  });

  it("names both periods in a legend and says what the chart leaves out", () => {
    render(<CategoryChart chart={COMPARED} current="1 – 27 Jul 2026" previous="1 – 27 Jun 2026" />);
    expect(screen.getByRole("list")).toHaveTextContent("1 – 27 Jun 20261 – 27 Jul 2026");
    expect(screen.getByText("2 more categories are in the table below.")).toBeInTheDocument();
  });

  it("has no legend for a single period, which its title already names", () => {
    const single: Chart = {
      ...COMPARED,
      groups: [{ ...GROCERIES, previous: null }],
      hidden: 0,
    };
    render(<CategoryChart chart={single} current="1 – 27 Jul 2026" previous={null} />);
    expect(screen.queryByText("1 – 27 Jun 2026")).not.toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Groceries, 1 – 27 Jul 2026: 742.60" }),
    ).toBeInTheDocument();
  });
});

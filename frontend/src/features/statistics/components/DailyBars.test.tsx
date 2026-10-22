import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
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

const lidl = {
  id: "r1",
  merchant_name: "Lidl",
  transaction_date: "2026-10-01T10:00:00Z",
  created_at: "2026-10-01T10:00:00Z",
  status: "parsed",
  total_amount: "120.00",
};

describe("DailyBars", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    localStorage.clear();
    rootStore = new RootStore();
    vi.spyOn(apiClient, "GET").mockImplementation(
      (_path: string, init: { params: { query: { start: string } } }) =>
        Promise.resolve({
          data: { items: init.params.query.start === "2026-10-01" ? [lidl] : [] },
          response: new Response(),
        }),
    );
  });

  const renderChart = () =>
    render(
      <StoreProvider store={rootStore}>
        <DailyBars daily={daily} currency="PLN" today="2026-10-04" />
      </StoreProvider>,
    );

  it("opens on the latest day with spending and names a day when its bar is tapped", () => {
    renderChart();

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
    renderChart();

    expect(screen.getAllByRole("button", { name: /October/ })).toHaveLength(4);
  });

  it("lists the receipts of the day tapped, and says when a day has none", async () => {
    renderChart();
    expect(screen.queryByRole("heading", { name: /Receipts of/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "1 October, 120 PLN" }));
    expect(apiClient.GET).toHaveBeenCalledWith("/receipts", {
      params: { query: { page: 1, size: 50, start: "2026-10-01", end: "2026-10-01" } },
    });
    expect(screen.getByRole("heading", { name: "Receipts of 1 October" })).toBeInTheDocument();
    expect(await screen.findByText("Lidl")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "2 October, 0 PLN" }));
    expect(await screen.findByText("No receipts that day.")).toBeInTheDocument();
  });

  it("draws the days as rows or a calendar, and remembers the choice", () => {
    renderChart();

    fireEvent.click(screen.getByRole("button", { name: "Days" }));
    // Rows are the days something was bought.
    expect(screen.getAllByRole("button", { name: /October/ })).toHaveLength(2);
    expect(screen.getByText("120 PLN")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(screen.getAllByRole("button", { name: /October/ })).toHaveLength(4);
    expect(localStorage.getItem("budget_chart_view")).toBe("calendar");
    expect(new RootStore().statisticsStore.chartView).toBe("calendar");
  });
});

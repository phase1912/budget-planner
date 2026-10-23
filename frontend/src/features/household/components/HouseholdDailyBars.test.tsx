import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { HouseholdDailyBars } from "./HouseholdDailyBars";

const ME = "u-me";
const ANNA = "u-anna";

const receipts = [
  {
    id: "r1",
    user_id: ANNA,
    merchant_name: "YouTube",
    total: "60.00",
    purchased_at: "2026-10-02T10:00:00Z",
  },
  {
    id: "r2",
    user_id: ME,
    merchant_name: "Lidl",
    total: "30.00",
    purchased_at: "2026-10-02T09:00:00Z",
  },
];

describe("HouseholdDailyBars (F23.22.3)", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    localStorage.clear();
    rootStore = new RootStore();
    rootStore.authStore.user = { id: ME } as typeof rootStore.authStore.user;
    rootStore.householdStore.daily = {
      members: [
        { user_id: ME, first_name: "Bohdan" },
        { user_id: ANNA, first_name: "Anna" },
      ],
      days: [
        {
          day: "2026-10-01",
          members: [
            { user_id: ME, total: "0" },
            { user_id: ANNA, total: "0" },
          ],
        },
        {
          day: "2026-10-02",
          members: [
            { user_id: ME, total: "30.00" },
            { user_id: ANNA, total: "60.00" },
          ],
        },
      ],
      undated_private: "0",
    };
    vi.spyOn(apiClient, "GET").mockResolvedValue({
      data: receipts,
      response: new Response(),
    });
  });

  const renderChart = () =>
    render(
      <StoreProvider store={rootStore}>
        <HouseholdDailyBars currency="PLN" today="2026-10-02" />
      </StoreProvider>,
    );

  it("lists the family's receipts of the day tapped, saying whose each is", async () => {
    renderChart();

    fireEvent.click(screen.getByRole("button", { name: /^2 October/ }));

    expect(apiClient.GET).toHaveBeenCalledWith("/api/v1/household/receipts", {
      params: { query: { start: "2026-10-02", end: "2026-10-02" } },
    });
    const anna = (await screen.findByText("YouTube")).closest("li");
    expect(anna).not.toBeNull();
    expect(within(anna as HTMLElement).getByText("Anna")).toBeInTheDocument();
    fireEvent.click(within(anna as HTMLElement).getByRole("button"));
    expect(rootStore.receiptStore.selectedReceiptId).toBe("r1");
  });

  it("draws the family's days as rows or a calendar too", () => {
    renderChart();

    fireEvent.click(screen.getByRole("button", { name: "Days" }));
    expect(screen.getAllByRole("button", { name: /October/ })).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(screen.getAllByRole("button", { name: /October/ })).toHaveLength(2);
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { RootStore } from "@/stores/RootStore";
import type { Household } from "@/stores/HouseholdStore";
import { StoreProvider } from "@/stores/StoreContext";
import { HouseholdMonthView } from "./HouseholdMonthView";
import { HouseholdStatisticsView } from "./HouseholdStatisticsView";
import { HouseholdViewSwitch } from "./HouseholdViewSwitch";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), use: vi.fn() },
}));

const api = apiClient as unknown as Record<"GET", ReturnType<typeof vi.fn>>;

const HOME: Household = {
  id: "h1",
  name: "Home",
  my_role: "owner",
  budget_limit: "1000.00",
  invite_code: "c0de",
  members: [
    {
      user_id: "me",
      first_name: "Bohdan",
      last_name: "R",
      email: "b@x",
      role: "owner",
      joined_at: "",
    },
    {
      user_id: "anna",
      first_name: "Anna",
      last_name: "R",
      email: "a@x",
      role: "member",
      joined_at: "",
    },
  ],
};

function renderWith(store: RootStore, node: React.ReactNode) {
  return render(<StoreProvider store={store}>{node}</StoreProvider>);
}

describe("household views (F12.5)", () => {
  let store: RootStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new RootStore();
    store.householdStore.household = HOME;
  });

  it("switches between my figures and the household's", () => {
    renderWith(store, <HouseholdViewSwitch />);

    fireEvent.click(screen.getByRole("button", { name: "Home" }));

    expect(store.householdStore.showingHousehold).toBe(true);
  });

  it("offers no switch to a household of one", () => {
    store.householdStore.household = { ...HOME, members: HOME.members.slice(0, 1) };
    renderWith(store, <HouseholdViewSwitch />);

    expect(screen.queryByRole("button", { name: "Home" })).not.toBeInTheDocument();
  });

  it("shows the month against the household budget and who spent what", async () => {
    api.GET.mockResolvedValue({
      data: {
        year: 2026,
        month: 10,
        total: "250.00",
        receipt_count: 3,
        is_complete: false,
        days_elapsed: 10,
        days: 31,
        excluded_count: 0,
        excluded_amount: "0",
        limit: { limit: "1000.00", percent: 25, remaining: "750.00" },
        members: [
          {
            user_id: "anna",
            first_name: "Anna",
            shared_total: "30.00",
            private_total: "120.00",
            total: "150.00",
          },
          {
            user_id: "me",
            first_name: "Bohdan",
            shared_total: "100.00",
            private_total: "0",
            total: "100.00",
          },
        ],
      },
    });
    renderWith(store, <HouseholdMonthView year={2026} month={10} currency="PLN" />);

    expect(await screen.findByText("250.00")).toBeInTheDocument();
    expect(screen.getByText(/25% of/)).toBeInTheDocument();
    expect(screen.getByText("Anna")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("of which private: 120.00 PLN")).toBeInTheDocument();
    expect(api.GET).toHaveBeenCalledWith(
      "/api/v1/household/months/{year}/{month}",
      expect.objectContaining({
        params: expect.objectContaining({ path: { year: 2026, month: 10 } }) as unknown,
      }),
    );
  });

  it("ranks the household's categories with private spending as one row", async () => {
    api.GET.mockResolvedValue({
      data: {
        start: "2026-10-01",
        end: "2026-10-31",
        total: "100.00",
        categories: [
          {
            category_id: "g",
            name: "Groceries",
            owner_id: null,
            item_count: 3,
            total: "70.00",
            share: "70.0",
          },
          {
            category_id: "p",
            name: "Pets",
            owner_id: "anna",
            item_count: 1,
            total: "10.00",
            share: "10.0",
          },
        ],
        private_total: "20.00",
        private_share: "20.0",
      },
    });
    renderWith(
      store,
      <HouseholdStatisticsView start="2026-10-01" end="2026-10-31" currency="PLN" />,
    );

    expect(await screen.findByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("Anna's")).toBeInTheDocument();
    expect(screen.getByText("Private")).toBeInTheDocument();
    expect(screen.getByText("20%")).toBeInTheDocument();
  });

  it("says so when nobody in the household has receipts in the period", async () => {
    api.GET.mockResolvedValue({
      data: {
        start: "a",
        end: "b",
        total: "0",
        categories: [],
        private_total: "0",
        private_share: "0",
      },
    });
    renderWith(store, <HouseholdStatisticsView start="a" end="b" currency="PLN" />);

    expect(await screen.findByText(/No receipts from anyone/)).toBeInTheDocument();
  });

  it("asks again when the month changes", async () => {
    api.GET.mockResolvedValue({ error: { detail: "x" } });
    const { rerender } = renderWith(
      store,
      <HouseholdMonthView year={2026} month={10} currency="PLN" />,
    );
    rerender(
      <StoreProvider store={store}>
        <HouseholdMonthView year={2026} month={9} currency="PLN" />
      </StoreProvider>,
    );

    await waitFor(() => {
      expect(api.GET).toHaveBeenCalledTimes(2);
    });
  });

  it("keeps the period asked for last when an older answer arrives late", async () => {
    let answerOctober: (value: unknown) => void = () => undefined;
    const stats = (total: string) => ({
      data: {
        start: "",
        end: "",
        total,
        categories: [],
        private_total: total,
        private_share: "100.0",
      },
    });
    const late = new Promise((resolve) => {
      answerOctober = resolve;
    });
    api.GET.mockReturnValueOnce(late).mockResolvedValueOnce(stats("690.10"));

    const october = store.householdStore.loadStatistics("2026-10-01", "2026-10-10");
    await store.householdStore.loadStatistics("2026-09-01", "2026-09-30");
    answerOctober(stats("19.46"));
    await october;

    expect(store.householdStore.statistics?.total).toBe("690.10");
  });
});

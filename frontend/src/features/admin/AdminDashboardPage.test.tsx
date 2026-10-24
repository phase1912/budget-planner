import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UsageReport } from "@/stores/AnalyticsStore";
import { AdminDashboardPage } from "./AdminDashboardPage";

const REPORT: UsageReport = {
  start: "2026-10-11",
  end: "2026-10-17",
  visits: 40,
  page_views: 55,
  views_by_page: [{ name: "/", count: 30 }],
  visits_by_source: [
    { name: "direct", count: 25 },
    { name: "google.com", count: 15 },
  ],
  visits_by_platform: [
    { name: "web", count: 30 },
    { name: "ios-app", count: 10 },
  ],
  visits_by_system: [
    { name: "android", count: 22 },
    { name: "ios", count: 18 },
  ],
  sign_ups: 3,
  confirmed: 2,
  with_a_receipt: 1,
  uploads: 5,
  receipts_read: 6,
  active_week: 2,
  active_month: 4,
  returning: 1,
  days: [
    {
      day: "2026-10-17",
      visits: 10,
      page_views: 14,
      sign_ups: 1,
      confirmations: 1,
      receipts_read: 2,
    },
  ],
};

const stores = vi.hoisted(() => ({
  authStore: { user: ((isAdmin: boolean) => ({ is_admin: isAdmin }))(true) },
  analyticsStore: {
    report: null as UsageReport | null,
    reportState: { error: null as string | null },
    period: "last_7",
    loadReport: vi.fn(),
    choosePeriod: vi.fn(),
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderPage = () =>
  render(
    <MemoryRouter>
      <AdminDashboardPage />
    </MemoryRouter>,
  );

describe("AdminDashboardPage (F17.3.3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.authStore.user = { is_admin: true };
    stores.analyticsStore.report = REPORT;
  });

  it("shows an admin the counts, the funnel and where visitors came from", () => {
    renderPage();

    expect(stores.analyticsStore.loadReport).toHaveBeenCalled();
    expect(screen.getByText("Visits").nextSibling).toHaveTextContent("40");
    expect(screen.getByText("Page views").nextSibling).toHaveTextContent("55");
    expect(screen.getByText("Came back from last week").nextSibling).toHaveTextContent("1");
    expect(screen.getByRole("heading", { name: "From visit to first receipt" })).toBeVisible();
    expect(screen.getByText("Direct or unknown")).toBeInTheDocument();
    expect(screen.getByText("visits: 10 · sign-ups: 1 · read: 2")).toBeInTheDocument();
  });

  it("says what visits were opened in and on which system (F17.3.4)", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Opened in" })).toBeVisible();
    expect(screen.getByText("iPhone app")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Operating system" })).toBeVisible();
    expect(screen.getByText("Android")).toBeInTheDocument();
  });
});

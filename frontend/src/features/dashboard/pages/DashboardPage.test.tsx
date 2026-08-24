import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";

// Mock the store context
vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    authStore: {
      user: { email: "test@example.com", first_name: "Anna", last_name: "Smith", currency: "PLN" },
    },
  }),
}));

describe("DashboardPage", () => {
  it("renders the dashboard layout with correct greeting", () => {
    // Mock time to 19:00 (Good evening)
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 0, 1, 19));
    
    try {
      render(
        <BrowserRouter>
          <DashboardPage />
        </BrowserRouter>,
      );

      expect(screen.getByText("Good evening, Anna")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Good evening, Anna" })).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});

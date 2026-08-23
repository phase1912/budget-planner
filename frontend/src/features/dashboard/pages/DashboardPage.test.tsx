import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";

// Mock the store context
vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    authStore: {
      user: { email: "test@example.com" },
    },
  }),
}));

describe("DashboardPage", () => {
  it("renders the dashboard for authenticated users", () => {
    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>,
    );
    expect(screen.getByRole("heading", { name: /welcome back!/i })).toBeInTheDocument();
    expect(screen.getByText(/test@example.com/i)).toBeInTheDocument();
  });
});

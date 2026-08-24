import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { App } from "./App";

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    authStore: {
      isAuthenticated: false,
    },
    themeStore: {
      theme: "light",
      toggleTheme: vi.fn(),
    },
    toastStore: {
      toasts: [],
      addToast: vi.fn(),
      removeToast: vi.fn(),
    },
  }),
}));

describe("App Router", () => {
  it("renders PublicLandingPage by default when not authenticated", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "Photograph a receipt. Get a budget." }),
    ).toBeInTheDocument();
  });
});

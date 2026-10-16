import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    serverStore: { isWaking: false, wake: () => undefined },
    accountStore: { mustConfirm: false, state: { isLoading: false } },
    authStore: {
      isAuthenticated: false,
    },
    languageStore: { language: "en", choose: vi.fn() },
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
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Photograph a receipt. Get a budget." }),
    ).toBeInTheDocument();
  });
});

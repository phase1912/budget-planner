import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

vi.mock("@/platform", () => ({
  device: {
    kind: "ios",
    isApp: true,
    ready: () => Promise.resolve(),
    onBack: () => () => undefined,
    setDarkBars: () => Promise.resolve(),
    feel: () => Promise.resolve(),
  },
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    serverStore: { isWaking: false, wake: () => undefined },
    accountStore: { mustConfirm: false, state: { isLoading: false } },
    analyticsStore: { countView: () => undefined },
    authStore: {
      isAuthenticated: false,
      authState: { isLoading: false, error: null },
      secondFactorToken: null,
      login: vi.fn(),
    },
    languageStore: { language: "en", choose: vi.fn() },
    themeStore: { theme: "light", toggleTheme: vi.fn() },
    toastStore: { toasts: [], addToast: vi.fn(), removeToast: vi.fn() },
  }),
}));

/** Words that would offer the paid plan for sale, which a store app may not (F25.3.3). */
const SELLING = /\b(buy|upgrade|subscribe|pricing|per month)\b|zł|€|\$/i;

describe("the store app (F22.2.1, F25.3.3)", () => {
  it("opens on signing in, never on the website's landing with its offer", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.queryByRole("heading", { name: "Know where every cent went." }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/receipts a month/)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(SELLING);
  });
});

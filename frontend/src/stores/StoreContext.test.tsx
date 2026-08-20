import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RootStore } from "@/stores/RootStore";
import { StoreProvider, useStores } from "@/stores/StoreContext";

function ThemeProbe() {
  const { themeStore } = useStores();
  return <span>theme: {themeStore.theme}</span>;
}

describe("StoreContext", () => {
  it("throws when useStores is called outside a StoreProvider", () => {
    // Swallow the expected React error-boundary log noise for this negative case.
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    expect(() => render(<ThemeProbe />)).toThrow("useStores must be used within a StoreProvider");

    consoleError.mockRestore();
  });

  it("provides the injected store to descendants", () => {
    const store = new RootStore();
    store.themeStore.setTheme("dark");

    render(
      <StoreProvider store={store}>
        <ThemeProbe />
      </StoreProvider>,
    );

    expect(screen.getByText("theme: dark")).toBeInTheDocument();
  });

  it("instantiates its own RootStore when none is injected", () => {
    render(
      <StoreProvider>
        <ThemeProbe />
      </StoreProvider>,
    );

    expect(screen.getByText(/theme: (light|dark)/)).toBeInTheDocument();
  });
});

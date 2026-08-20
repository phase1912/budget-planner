import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { THEME_STORAGE_KEY, ThemeStore } from "@/stores/ThemeStore";

function mockMatchMedia(prefersDark: boolean): void {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-color-scheme: dark)" && prefersDark,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

describe("ThemeStore", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("defaults to the OS prefers-color-scheme when nothing is stored", () => {
    mockMatchMedia(true);

    const store = new ThemeStore();

    expect(store.theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("defaults to light when the OS has no dark preference", () => {
    mockMatchMedia(false);

    const store = new ThemeStore();

    expect(store.theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("prefers a stored theme over the OS default", () => {
    mockMatchMedia(true);
    localStorage.setItem(THEME_STORAGE_KEY, "light");

    const store = new ThemeStore();

    expect(store.theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("setTheme persists the choice and toggles the .dark class", () => {
    mockMatchMedia(false);
    const store = new ThemeStore();

    store.setTheme("dark");

    expect(store.theme).toBe("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("toggleTheme flips between light and dark", () => {
    mockMatchMedia(false);
    const store = new ThemeStore();

    store.toggleTheme();
    expect(store.theme).toBe("dark");

    store.toggleTheme();
    expect(store.theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});

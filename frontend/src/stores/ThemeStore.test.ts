import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DARK_AT_NIGHT_STORAGE_KEY, THEME_STORAGE_KEY, ThemeStore } from "@/stores/ThemeStore";

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

const root = () => document.documentElement;

describe("ThemeStore (F23.1)", () => {
  beforeEach(() => {
    localStorage.clear();
    root().classList.remove("dark");
    delete root().dataset.palette;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("opens in Midnight, the dark default, when nothing is chosen", () => {
    mockMatchMedia(false);

    const store = new ThemeStore();

    expect(store.palette).toBe("midnight");
    expect(store.theme).toBe("dark");
    expect(root().classList.contains("dark")).toBe(true);
    expect(root().dataset.palette).toBe("midnight");
  });

  it("reads a light or dark theme kept from before palettes as Daylight or Midnight", () => {
    mockMatchMedia(true);
    localStorage.setItem(THEME_STORAGE_KEY, "light");

    expect(new ThemeStore().palette).toBe("daylight");
  });

  it("keeps a chosen palette and paints with it, light palettes without .dark", () => {
    mockMatchMedia(false);
    const store = new ThemeStore();

    store.setPalette("rose");

    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("rose");
    expect(root().dataset.palette).toBe("rose");
    expect(root().classList.contains("dark")).toBe(false);
  });

  it("turns a light palette into Midnight at night only when asked to", () => {
    mockMatchMedia(true);
    const store = new ThemeStore();
    store.setPalette("lavender");
    expect(store.effective).toBe("lavender");

    store.setDarkAtNight(true);

    expect(localStorage.getItem(DARK_AT_NIGHT_STORAGE_KEY)).toBe("1");
    expect(store.effective).toBe("midnight");
    expect(root().classList.contains("dark")).toBe(true);
    store.setSystemDark(false);
    expect(store.effective).toBe("lavender");
  });

  it("takes the account's palette on sign-in and ignores one it does not know", () => {
    mockMatchMedia(false);
    const store = new ThemeStore();

    store.adoptAccount("ocean", false);
    expect(store.palette).toBe("ocean");
    store.adoptAccount("neon", undefined);
    expect(store.palette).toBe("ocean");
  });

  it("the header's switch flips between the two base looks", () => {
    mockMatchMedia(false);
    const store = new ThemeStore();

    store.toggleTheme();
    expect(store.palette).toBe("daylight");
    store.toggleTheme();
    expect(store.palette).toBe("midnight");
  });
});

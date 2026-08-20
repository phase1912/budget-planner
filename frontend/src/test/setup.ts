import "@testing-library/jest-dom/vitest";

// jsdom does not implement matchMedia. Default to "no dark preference" so any store
// or component that reads it (e.g. ThemeStore, F9.2.3) has a stable baseline; tests
// that care about a specific OS preference override this with vi.stubGlobal.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }),
});

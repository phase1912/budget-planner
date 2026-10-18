import { makeAutoObservable } from "mobx";

export type Theme = "light" | "dark";
export type Palette = "midnight" | "daylight" | "rose" | "lavender" | "sage" | "ocean";

/** The palettes in the order the pickers show them; `dark` says which base each builds on. */
export const PALETTES: readonly { id: Palette; dark: boolean }[] = [
  { id: "midnight", dark: true },
  { id: "daylight", dark: false },
  { id: "rose", dark: false },
  { id: "lavender", dark: false },
  { id: "sage", dark: false },
  { id: "ocean", dark: true },
];

export const DEFAULT_PALETTE: Palette = "midnight";
export const THEME_STORAGE_KEY = "budget-planner.theme";
export const DARK_AT_NIGHT_STORAGE_KEY = "budget-planner.dark-at-night";

const DARK_QUERY = "(prefers-color-scheme: dark)";

export function isPalette(value: unknown): value is Palette {
  return PALETTES.some((p) => p.id === value);
}

function isDarkPalette(palette: Palette): boolean {
  return PALETTES.find((p) => p.id === palette)?.dark ?? false;
}

/** The stored palette; "light" and "dark" from before palettes are Daylight and Midnight. */
function readStoredPalette(): Palette {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light") return "daylight";
  if (stored === "dark") return "midnight";
  return isPalette(stored) ? stored : DEFAULT_PALETTE;
}

/**
 * Owns how the product looks (F9.2.3, F23.1): one of six palettes, Midnight unless the
 * user chose another, and optionally Midnight whenever the device is dark. It sets the
 * `.dark` class and `data-palette` the design tokens key off, so components never branch
 * on the look. The account keeps the choice for other devices; this store keeps it for
 * this browser and the first paint (index.html).
 */
export class ThemeStore {
  palette: Palette;
  darkAtNight: boolean;
  systemDark: boolean;

  constructor() {
    this.palette = readStoredPalette();
    this.darkAtNight = localStorage.getItem(DARK_AT_NIGHT_STORAGE_KEY) === "1";
    const query = window.matchMedia(DARK_QUERY);
    this.systemDark = query.matches;
    makeAutoObservable(this);
    query.addEventListener("change", (event) => {
      this.setSystemDark(event.matches);
    });
    this.apply();
  }

  /** The palette on screen: the chosen one, or Midnight at night when that is asked for. */
  get effective(): Palette {
    if (this.darkAtNight && this.systemDark && !isDarkPalette(this.palette)) return "midnight";
    return this.palette;
  }

  get theme(): Theme {
    return isDarkPalette(this.effective) ? "dark" : "light";
  }

  setPalette(palette: Palette): void {
    this.palette = palette;
    localStorage.setItem(THEME_STORAGE_KEY, palette);
    this.apply();
  }

  setDarkAtNight(on: boolean): void {
    this.darkAtNight = on;
    localStorage.setItem(DARK_AT_NIGHT_STORAGE_KEY, on ? "1" : "0");
    this.apply();
  }

  /** The header's quick switch: between the chosen look and its opposite base. */
  toggleTheme(): void {
    this.setPalette(this.theme === "dark" ? "daylight" : "midnight");
  }

  /** Take the account's choice on sign-in; nothing chosen there keeps this browser's. */
  adoptAccount(palette: string | null | undefined, darkAtNight: boolean | undefined): void {
    if (isPalette(palette)) this.setPalette(palette);
    if (darkAtNight !== undefined) this.setDarkAtNight(darkAtNight);
  }

  setSystemDark(dark: boolean): void {
    this.systemDark = dark;
    this.apply();
  }

  private apply(): void {
    const root = document.documentElement;
    root.classList.toggle("dark", this.theme === "dark");
    root.dataset.palette = this.effective;
  }
}

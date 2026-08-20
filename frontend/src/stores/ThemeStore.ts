import { makeAutoObservable } from "mobx";

export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "budget-planner.theme";

function readStoredTheme(): Theme | null {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : null;
}

function prefersDarkColorScheme(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/**
 * Owns the light/dark theme preference (F9.2.3). Falls back to the OS
 * prefers-color-scheme when the user has not chosen a theme yet, persists any
 * explicit choice to localStorage, and toggles the `.dark` class the design tokens
 * (F9.6) key off — component styling never branches on theme itself.
 */
export class ThemeStore {
  theme: Theme;

  constructor() {
    this.theme = readStoredTheme() ?? (prefersDarkColorScheme() ? "dark" : "light");
    makeAutoObservable(this);
    this.applyThemeClass();
  }

  setTheme(theme: Theme): void {
    this.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    this.applyThemeClass();
  }

  toggleTheme(): void {
    this.setTheme(this.theme === "dark" ? "light" : "dark");
  }

  private applyThemeClass(): void {
    document.documentElement.classList.toggle("dark", this.theme === "dark");
  }
}

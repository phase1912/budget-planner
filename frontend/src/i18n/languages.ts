/** The languages the product is written in (F9.9), and how each formats dates and amounts. */
export const LANGUAGES = ["en", "uk", "pl"] as const;
export type Language = (typeof LANGUAGES)[number];

/** Each language named in itself, as a switcher lists them. */
export const LANGUAGE_NAMES: Record<Language, string> = {
  en: "English",
  uk: "Українська",
  pl: "Polski",
};

/** The Intl locale whose dates and amounts read naturally in each language. */
export const LOCALES: Record<Language, string> = { en: "en-GB", uk: "uk-UA", pl: "pl-PL" };

export const STORAGE_KEY = "budget_language";

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && (LANGUAGES as readonly string[]).includes(value);
}

/**
 * The first of the browser's languages the product is written in, else English.
 *
 * By language, never by where the user is: a Ukrainian living in Poland reads Ukrainian
 * (F9.9). "uk-UA" and "pl-PL" count as "uk" and "pl".
 */
export function browserLanguage(preferred: readonly string[]): Language {
  for (const tag of preferred) {
    const base = tag.toLowerCase().split("-")[0];
    if (isLanguage(base)) return base;
  }
  return "en";
}

/** The language a public page's address names: "/uk" is Ukrainian (F17.2), "/" none. */
export function addressLanguage(pathname: string): Language | null {
  const first = pathname.split("/")[1] ?? "";
  return isLanguage(first) && pathname.replace(/\/+$/, "") === `/${first}` ? first : null;
}

/**
 * The language to start in: the one a public page's address names, else the one chosen on
 * this browser before, else the browser's own. Opening "/uk" from a search result reads
 * Ukrainian, and counts as choosing it.
 */
export function initialLanguage(): Language {
  const fromAddress = typeof location === "undefined" ? null : addressLanguage(location.pathname);
  if (fromAddress) return fromAddress;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isLanguage(saved)) return saved;
  } catch {
    // Storage blocked: the browser's language still applies.
  }
  return browserLanguage(typeof navigator === "undefined" ? [] : navigator.languages);
}

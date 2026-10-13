import i18n from "i18next";

import { LOCALES, isLanguage } from "./languages";

/** The Intl locale of the language the product is shown in right now. */
export function currentLocale(): string {
  const language = i18n.language;
  return isLanguage(language) ? LOCALES[language] : LOCALES.en;
}

interface Formatter<T> {
  format(value: T): string;
}

const numbers = new Map<string, Intl.NumberFormat>();
const dates = new Map<string, Intl.DateTimeFormat>();

/**
 * An Intl.NumberFormat that formats in the current language each time it is used, so a
 * formatter made once at module level follows a change of language (F9.9).
 */
export function numberFormat(options: Intl.NumberFormatOptions): Formatter<number | bigint> {
  return {
    format(value) {
      const key = currentLocale() + JSON.stringify(options);
      let formatter = numbers.get(key);
      if (!formatter) {
        formatter = new Intl.NumberFormat(currentLocale(), options);
        numbers.set(key, formatter);
      }
      return formatter.format(value);
    },
  };
}

/** The same for dates: an Intl.DateTimeFormat in whatever language is current (F9.9). */
export function dateFormat(options: Intl.DateTimeFormatOptions): Formatter<Date | number> {
  return {
    format(value) {
      const key = currentLocale() + JSON.stringify(options);
      let formatter = dates.get(key);
      if (!formatter) {
        formatter = new Intl.DateTimeFormat(currentLocale(), options);
        dates.set(key, formatter);
      }
      return formatter.format(value);
    },
  };
}

const AMOUNT = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** A sum of money to the cent, as the current language writes it: "1 234,50" in Polish. */
export function formatAmount(value: number | string): string {
  return AMOUNT.format(Number(value));
}

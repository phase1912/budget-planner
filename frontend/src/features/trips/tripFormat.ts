import { currentLocale, dateFormat } from "@/i18n/format";

const DAY = dateFormat({ day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/** A trip's day ("2026-10-03") as the current language writes it. */
export function formatTripDay(day: string): string {
  return DAY.format(new Date(`${day}T00:00:00Z`));
}

// ISO 3166-1 alpha-2: Intl names them, but cannot list them.
const COUNTRY_CODES =
  "AD AE AF AG AL AM AO AR AT AU AZ BA BB BD BE BF BG BH BI BJ BN BO BR BS BT BW BY BZ CA CD CF CG CH CI CL CM CN CO CR CU CV CY CZ DE DJ DK DM DO DZ EC EE EG ER ES ET FI FJ FR GA GB GD GE GH GM GN GQ GR GT GW GY HK HN HR HT HU ID IE IL IN IQ IR IS IT JM JO JP KE KG KH KM KN KP KR KW KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MG MK ML MM MN MT MU MV MW MX MY MZ NA NE NG NI NL NO NP NZ OM PA PE PG PH PK PL PS PT PY QA RO RS RW SA SC SD SE SG SI SK SL SM SN SO SR SS SV SY SZ TD TG TH TJ TL TM TN TR TT TW TZ UA UG US UY UZ VA VC VE VN YE ZA ZM ZW".split(
    " ",
  );

/** A country's name in the current language, or the code when the browser has none. */
export function countryName(code: string): string {
  try {
    return new Intl.DisplayNames([currentLocale()], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

/** Every country to pick from, by name in the current language. */
export function countryOptions(): { code: string; name: string }[] {
  return COUNTRY_CODES.map((code) => ({ code, name: countryName(code) })).sort((a, b) =>
    a.name.localeCompare(b.name, currentLocale()),
  );
}

/**
 * Every currency an expense may have been paid in, the account's first, named in the
 * current language: a trip abroad pays in whatever the country uses (F20.5).
 */
export function paidCurrencyOptions(accountCurrency: string): { code: string; name: string }[] {
  const names = new Intl.DisplayNames([currentLocale()], { type: "currency" });
  const codes = Intl.supportedValuesOf("currency").filter((code) => code !== accountCurrency);
  return [accountCurrency, ...codes].map((code) => ({
    code,
    name: `${code} — ${names.of(code) ?? code}`,
  }));
}

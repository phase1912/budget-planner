/**
 * What the first sign-in proposes before the user says anything (F23.9): the currency of
 * the country the browser is set to, by its time zone and then its language. Only a
 * proposal — every one can be changed on the same screen.
 */
const BY_ZONE: Record<string, string> = {
  "Europe/Warsaw": "PLN",
  "Europe/Kyiv": "UAH",
  "Europe/Kiev": "UAH",
  "Europe/London": "GBP",
};
const EURO_ZONES = [
  "Berlin",
  "Paris",
  "Madrid",
  "Rome",
  "Vienna",
  "Amsterdam",
  "Brussels",
  "Dublin",
  "Lisbon",
  "Helsinki",
  "Athens",
  "Vilnius",
  "Riga",
  "Tallinn",
  "Bratislava",
  "Ljubljana",
];

export function guessCurrency(timeZone: string, language: string): string {
  if (BY_ZONE[timeZone]) return BY_ZONE[timeZone];
  if (EURO_ZONES.some((city) => timeZone === `Europe/${city}`)) return "EUR";
  if (timeZone.startsWith("America/") && language.endsWith("US")) return "USD";
  if (language.startsWith("pl")) return "PLN";
  if (language.startsWith("uk")) return "UAH";
  return "EUR";
}

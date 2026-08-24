export const SUPPORTED_CURRENCIES = [
  { code: "USD", name: "US Dollar" },
  { code: "EUR", name: "Euro" },
  { code: "PLN", name: "Polish Złoty" },
  { code: "UAH", name: "Ukrainian Hryvnia" },
  { code: "GBP", name: "British Pound" },
] as const;

export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number]["code"];

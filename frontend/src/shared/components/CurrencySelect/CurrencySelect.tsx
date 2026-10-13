import { Select, type SelectProps } from "@/shared/components/Select/Select";
import { SUPPORTED_CURRENCIES } from "@/config/currencies";
import { useTranslation } from "react-i18next";
import { currentLocale } from "@/i18n/format";

export type CurrencySelectProps = Omit<SelectProps, "children">;

/** Currencies named in the language the app is shown in, by the browser's own Intl data. */
export function CurrencySelect(props: CurrencySelectProps) {
  // English keeps the names as written here; other languages take the browser's own.
  const { i18n } = useTranslation();
  const names =
    i18n.language === "en" ? null : new Intl.DisplayNames([currentLocale()], { type: "currency" });
  return (
    <Select {...props}>
      {SUPPORTED_CURRENCIES.map((currency) => (
        <option key={currency.code} value={currency.code}>
          {currency.code} — {names?.of(currency.code) ?? currency.name}
        </option>
      ))}
    </Select>
  );
}

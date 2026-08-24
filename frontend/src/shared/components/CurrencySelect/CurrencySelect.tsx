import { Select, type SelectProps } from "@/shared/components/Select/Select";
import { SUPPORTED_CURRENCIES } from "@/config/currencies";

export type CurrencySelectProps = Omit<SelectProps, "children">;

export function CurrencySelect(props: CurrencySelectProps) {
  return (
    <Select {...props}>
      {SUPPORTED_CURRENCIES.map((currency) => (
        <option key={currency.code} value={currency.code}>
          {currency.code} — {currency.name}
        </option>
      ))}
    </Select>
  );
}

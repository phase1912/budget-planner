import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CurrencySelect } from "./CurrencySelect";
import { SUPPORTED_CURRENCIES } from "@/config/currencies";

describe("CurrencySelect", () => {
  it("renders all supported currencies as options", () => {
    render(<CurrencySelect aria-label="Currency" />);

    const select = screen.getByRole("combobox", { name: "Currency" });
    expect(select).toBeInTheDocument();

    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(SUPPORTED_CURRENCIES.length);

    SUPPORTED_CURRENCIES.forEach((currency) => {
      const option = screen.getByRole("option", { name: `${currency.code} — ${currency.name}` });
      expect(option).toBeInTheDocument();
      expect(option).toHaveAttribute("value", currency.code);
    });
  });
});

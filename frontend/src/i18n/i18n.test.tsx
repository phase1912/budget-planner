import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import i18n from "@/i18n";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { dateFormat, numberFormat } from "./format";
import { browserLanguage } from "./languages";

describe("the language the product opens in (F9.9)", () => {
  it("is the first of the browser's languages it is written in", () => {
    expect(browserLanguage(["de-DE", "uk-UA", "en-US"])).toBe("uk");
    expect(browserLanguage(["pl"])).toBe("pl");
  });

  it("is English when the browser asks for none of them", () => {
    expect(browserLanguage(["ru-RU", "de"])).toBe("en");
    expect(browserLanguage([])).toBe("en");
  });
});

describe("text, amounts and dates in the chosen language", () => {
  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("formats amounts and dates as each language writes them", async () => {
    const amount = numberFormat({ minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const month = dateFormat({ month: "long", timeZone: "UTC" });
    const october = Date.UTC(2026, 9, 5);

    expect([amount.format(12345.5), month.format(october)]).toEqual(["12,345.50", "October"]);
    await i18n.changeLanguage("pl");
    expect(amount.format(12345.5).replace(/\s/g, " ")).toBe("12 345,50");
    await i18n.changeLanguage("uk");
    expect(month.format(october)).toBe("жовтень");
  });

  it("uses each language's plural forms", () => {
    const t = i18n.getFixedT("pl", "household");
    const sentence = (count: number) =>
      t("join.invitesWithMembers", { count, owner: "A", name: "Dom" });

    expect(sentence(2)).toContain("2 osoby");
    expect(sentence(5)).toContain("5 osób");
    expect(
      i18n.getFixedT("uk", "household")("join.invitesWithMembers", {
        count: 5,
        owner: "A",
        name: "Дім",
      }),
    ).toContain("5 учасників");
  });

  it("shows a screen in the language picked", async () => {
    await i18n.changeLanguage("uk");
    render(
      <StoreProvider store={new RootStore()}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </StoreProvider>,
    );

    expect(screen.getByRole("heading", { name: "З поверненням" })).toBeInTheDocument();
    expect(screen.getByLabelText("Електронна пошта")).toBeInTheDocument();
  });
});

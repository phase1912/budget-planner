import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PublicLandingPage } from "./PublicLandingPage";

const languageStore = vi.hoisted(() => ({ language: "en", choose: vi.fn() }));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => ({ languageStore }) }));

function renderPage(language?: "en" | "uk" | "pl") {
  render(
    <MemoryRouter>
      <PublicLandingPage language={language} />
    </MemoryRouter>,
  );
}

describe("PublicLandingPage (F17.2, F17.11)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    languageStore.language = "en";
  });

  it("states the promise and leads to sign-up, sign-in and the tour", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { level: 1, name: "Know where every cent went." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start with one receipt" })).toHaveAttribute(
      "href",
      "/register",
    );
    expect(screen.getByRole("link", { name: "See what you can do" })).toHaveAttribute(
      "href",
      "#see",
    );
    expect(screen.getByRole("link", { name: "I already have one" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("names no country, shop or currency", () => {
    const { container } = render(
      <MemoryRouter>
        <PublicLandingPage />
      </MemoryRouter>,
    );

    expect(container.textContent).not.toMatch(/zł|PLN|złot|Biedronka|Lidl|NBP|Poland|Polish rules/);
  });

  it("shows every line where other apps show one total", () => {
    renderPage();

    const ours = screen.getByRole("region", { name: "Budget Agent sees every line" });
    expect(within(ours).getByText("Kids’ crayons")).toBeInTheDocument();
    expect(within(ours).getByText("Household")).toBeInTheDocument();
  });

  it("tours Home, Spending, Products and Plan one tab at a time", () => {
    renderPage();

    const tour = screen.getByRole("region", { name: "See what you can do" });
    expect(
      within(tour).getByRole("heading", { level: 3, name: "What is left this month" }),
    ).toBeInTheDocument();
    fireEvent.click(within(tour).getByRole("button", { name: "Products" }));
    expect(
      within(tour).getByRole("heading", { level: 3, name: "The same milk, cheaper next door" }),
    ).toBeInTheDocument();
    expect(within(tour).getByText("Price history per product and shop")).toBeInTheDocument();
  });

  it("lists what the product does and answers the usual questions", () => {
    renderPage();

    for (const title of [
      "Every line, not just the total",
      "Prices across your shops",
      "Income, taxes and bills",
      "One budget for the family",
      "Holidays and business trips",
      "Your receipts stay yours",
    ]) {
      expect(screen.getByRole("heading", { level: 3, name: title })).toBeInTheDocument();
    }
    const faq = screen.getByRole("region", { name: "Questions people ask" });
    expect(within(faq).getByText("Which countries and currencies?")).toBeInTheDocument();
    expect(within(faq).getByRole("link", { name: "All answers in Help" })).toHaveAttribute(
      "href",
      "/help",
    );
  });

  it("links each language's own address", () => {
    renderPage();

    const languages = screen.getByRole("navigation", { name: "Also in" });
    expect(within(languages).getByRole("link", { name: "Українська" })).toHaveAttribute(
      "href",
      "/uk",
    );
    expect(within(languages).getByRole("link", { name: "Polski" })).toHaveAttribute("href", "/pl");
  });

  it("leads to help, the privacy policy and the terms from the footer (F17.10)", () => {
    renderPage();

    const about = screen.getByRole("navigation", { name: "About the service" });
    expect(within(about).getByRole("link", { name: "Help" })).toHaveAttribute("href", "/help");
    expect(within(about).getByRole("link", { name: "Privacy policy" })).toHaveAttribute(
      "href",
      "/privacy",
    );
    expect(within(about).getByRole("link", { name: "Terms of use" })).toHaveAttribute(
      "href",
      "/terms",
    );
  });

  it("opening a language's address chooses that language", () => {
    renderPage("pl");

    expect(languageStore.choose).toHaveBeenCalledWith("pl");
  });

  it("keeps the sample screens away from screen readers", () => {
    const { container } = render(
      <MemoryRouter>
        <PublicLandingPage />
      </MemoryRouter>,
    );

    const phones = container.querySelectorAll("figure > div");
    expect(phones.length).toBe(4);
    phones.forEach((phone) => {
      expect(phone).toHaveAttribute("aria-hidden", "true");
    });
  });
});

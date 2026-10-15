import { render, screen, within } from "@testing-library/react";
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

describe("PublicLandingPage (F17.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    languageStore.language = "en";
  });

  it("states the promise and leads to sign-up and sign-in", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { level: 1, name: "Photograph a receipt. Get a budget." }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Create an account/ })[0]).toHaveAttribute(
      "href",
      "/register",
    );
    expect(screen.getAllByRole("link", { name: "I already have one" })[0]).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("walks through each thing the product does", () => {
    renderPage();

    for (const title of [
      "Every line, not just the total",
      "Where the money really goes",
      "Advice built from your purchases",
      "One budget for the family",
      "Holidays and business trips",
    ]) {
      expect(screen.getByRole("heading", { level: 3, name: title })).toBeInTheDocument();
    }
  });

  it("answers the usual questions", () => {
    renderPage();

    const faq = screen.getByRole("region", { name: "Questions" });
    expect(within(faq).getByText("Is it free?")).toBeInTheDocument();
    expect(
      within(faq).getByText("What if I paid in cash and have no receipt?"),
    ).toBeInTheDocument();
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

    const previews = container.querySelectorAll("figure");
    expect(previews.length).toBeGreaterThanOrEqual(5);
    previews.forEach((preview) => {
      expect(preview).toHaveAttribute("aria-hidden", "true");
    });
  });
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { LegalPage } from "./LegalPage";

describe("LegalPage (F17.9.4)", () => {
  it("states where data is processed and how long photos are kept", () => {
    render(
      <MemoryRouter>
        <LegalPage document="privacy" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Privacy policy" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Where, and who processes it" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Receipt photos and forwarded files: 90 days/)).toBeInTheDocument();
    expect(screen.getByText("Version of 22 October 2026")).toBeInTheDocument();
    expect(screen.getByText(/sets no cookies and loads nothing from other websites/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Help" })).toHaveAttribute("href", "/help");
  });

  it("shows the terms with every section", () => {
    render(
      <MemoryRouter>
        <LegalPage document="terms" />
      </MemoryRouter>,
    );

    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(6);
  });
});

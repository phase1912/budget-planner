import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LegalPage } from "./LegalPage";

describe("LegalPage (F17.9.4)", () => {
  it("states where data is processed and how long photos are kept", () => {
    render(<LegalPage document="privacy" />);

    expect(screen.getByRole("heading", { level: 1, name: "Privacy policy" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Where, and who processes it" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Receipt photos and forwarded files: 90 days/)).toBeInTheDocument();
    expect(screen.getByText("Version of 17 October 2026")).toBeInTheDocument();
  });

  it("shows the terms with every section", () => {
    render(<LegalPage document="terms" />);

    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(5);
  });
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SectionTabs } from "./SectionTabs";

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <SectionTabs />
    </MemoryRouter>,
  );
}

describe("SectionTabs", () => {
  it("puts Categories one tap away from Receipts on a phone", () => {
    renderAt("/receipts");
    expect(screen.getByRole("link", { name: "Receipts" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Categories" })).toHaveAttribute("href", "/categories");
  });

  it("marks Categories current on the taxonomy screen too", () => {
    renderAt("/categories/manage");
    expect(screen.getByRole("link", { name: "Categories" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});

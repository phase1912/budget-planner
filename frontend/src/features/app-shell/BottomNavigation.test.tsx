import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { BottomNavigation } from "./BottomNavigation";

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <BottomNavigation />
    </MemoryRouter>,
  );
}

describe("BottomNavigation (F23.2)", () => {
  it("offers the four places and adding a receipt as the centre button", () => {
    renderAt("/");
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    for (const [name, href] of [
      ["Spending", "/spending"],
      ["Add a receipt", "/upload"],
      ["Products", "/products"],
      ["Plan", "/plan"],
    ]) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });

  it("lights Spending on the receipts and categories reached from it, Plan on trips", () => {
    renderAt("/categories/manage");
    expect(screen.getByRole("link", { name: "Spending" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  });

  it("lights Plan on goals and trips", () => {
    renderAt("/trips/1");
    expect(screen.getByRole("link", { name: "Plan" })).toHaveAttribute("aria-current", "page");
  });
});

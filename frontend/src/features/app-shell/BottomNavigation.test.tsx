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

describe("BottomNavigation", () => {
  it("offers the phone's four tabs and upload as the centre button", () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    for (const [name, href] of [
      ["Receipts", "/receipts"],
      ["Upload a receipt", "/upload"],
      ["Stats", "/statistics"],
      ["Goals", "/goals"],
    ]) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    }
  });

  it("lights Receipts on the categories screens, which a phone reaches from there", () => {
    renderAt("/categories/manage");
    expect(screen.getByRole("link", { name: "Receipts" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  });
});

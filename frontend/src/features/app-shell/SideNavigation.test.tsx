import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { StoreProvider } from "@/stores/StoreContext";
import { SideNavigation } from "./SideNavigation";

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <StoreProvider>
        <SideNavigation />
      </StoreProvider>
    </MemoryRouter>,
  );
}

describe("SideNavigation (F23.2, F21.13.5)", () => {
  it("keeps adding a receipt as the main button and the assistant beside the brand", () => {
    renderAt("/");
    const links = screen.getAllByRole("link");

    expect(screen.getByRole("link", { name: "Add a receipt" })).toHaveAttribute("href", "/upload");
    expect(screen.getByRole("link", { name: "Assistant" })).toHaveAttribute("href", "/assistant");
    expect(links.map((l) => l.getAttribute("href")).slice(0, 3)).toEqual([
      "/",
      "/assistant",
      "/upload",
    ]);
  });

  it("lights the assistant while it is open", () => {
    renderAt("/assistant");
    expect(screen.getByRole("link", { name: "Assistant" })).toHaveAttribute("aria-current", "page");
  });
});

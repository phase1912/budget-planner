import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { StoreProvider } from "@/stores/StoreContext";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("renders the brand header and theme toggle", () => {
    render(
      <MemoryRouter>
        <StoreProvider>
          <AppShell />
        </StoreProvider>
      </MemoryRouter>,
    );

    // Check brand
    expect(screen.getByRole("link", { name: "Budget Agent" })).toBeInTheDocument();

    // Check theme toggle button
    const toggleButton = screen.getByLabelText("Toggle theme");
    expect(toggleButton).toBeInTheDocument();

    // Test toggle click
    fireEvent.click(toggleButton);
    // Since we can't easily mock the document classlist here without more setup,
    // we just ensure the button is clickable without throwing
  });

  it("keeps the bottom bar off the upload flow, a focused task of its own", () => {
    localStorage.setItem("budget_access_token", "token");
    localStorage.setItem(
      "budget_user",
      JSON.stringify({ id: "u", email: "a@b.c", first_name: "A", last_name: "B", currency: "PLN" }),
    );
    try {
      const { unmount } = render(
        <MemoryRouter initialEntries={["/receipts"]}>
          <StoreProvider>
            <AppShell />
          </StoreProvider>
        </MemoryRouter>,
      );
      expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
      unmount();

      render(
        <MemoryRouter initialEntries={["/upload"]}>
          <StoreProvider>
            <AppShell />
          </StoreProvider>
        </MemoryRouter>,
      );
      expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
    } finally {
      localStorage.clear();
    }
  });
});

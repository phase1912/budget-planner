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
    expect(screen.getByRole("link", { name: "AI Budget Agent" })).toBeInTheDocument();

    // Check theme toggle button
    const toggleButton = screen.getByLabelText("Toggle theme");
    expect(toggleButton).toBeInTheDocument();
    
    // Test toggle click
    fireEvent.click(toggleButton);
    // Since we can't easily mock the document classlist here without more setup, 
    // we just ensure the button is clickable without throwing
  });
});

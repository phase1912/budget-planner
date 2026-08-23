import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "@/App";

import { StoreProvider } from "@/stores/StoreContext";

// Proves the Vitest + RTL harness runs end-to-end in CI (F0.5, F9.1.3).
describe("App", () => {
  it("renders without crashing", () => {
    render(
      <StoreProvider>
        <App />
      </StoreProvider>,
    );
    expect(
      screen.getByRole("heading", { name: "Budgeting made simple with AI" }),
    ).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { PublicLandingScreen } from "./PublicLandingScreen";

describe("PublicLandingScreen", () => {
  it("renders the heading and action buttons", () => {
    render(
      <MemoryRouter>
        <PublicLandingScreen />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Budgeting made simple with AI" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
  });
});

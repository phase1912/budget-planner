import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { PublicLandingPage } from "./PublicLandingPage";

describe("PublicLandingPage", () => {
  it("renders the heading and action buttons", () => {
    render(
      <MemoryRouter>
        <PublicLandingPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Photograph a receipt. Get a budget." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "I already have one" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create an account" })).toBeInTheDocument();
  });
});

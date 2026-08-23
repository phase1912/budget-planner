import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { NotFoundScreen } from "./NotFoundScreen";

describe("NotFoundScreen", () => {
  it("renders the 404 message and return home button", () => {
    render(
      <MemoryRouter>
        <NotFoundScreen />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "404 - Page Not Found" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Return Home" })).toBeInTheDocument();
  });
});

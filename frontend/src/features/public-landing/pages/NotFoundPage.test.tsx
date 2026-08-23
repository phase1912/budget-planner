import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { NotFoundPage } from "./NotFoundPage";

describe("NotFoundPage", () => {
  it("renders the 404 message and return home button", () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "404 - Page Not Found" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Return Home" })).toBeInTheDocument();
  });
});

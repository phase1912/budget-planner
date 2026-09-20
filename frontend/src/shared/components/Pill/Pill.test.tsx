import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Pill } from "./Pill";

describe("Pill", () => {
  it("renders the neutral tone by default", () => {
    render(<Pill data-testid="pill">Uncategorized</Pill>);
    const pill = screen.getByTestId("pill");
    expect(pill).toHaveClass("bg-tone-neutral-bg");
    expect(pill).toHaveClass("text-tone-neutral-text");
  });

  it("renders tone classes", () => {
    render(
      <Pill tone="warning" data-testid="pill">
        Low confidence
      </Pill>,
    );
    const pill = screen.getByTestId("pill");
    expect(pill).toHaveClass("bg-tone-warning-bg");
    expect(pill).toHaveClass("text-tone-warning-text");
  });

  it("renders the compact size", () => {
    render(
      <Pill size="sm" data-testid="pill">
        Groceries
      </Pill>,
    );
    expect(screen.getByTestId("pill")).toHaveClass("px-[10px]");
  });

  it("keeps caller classes", () => {
    render(
      <Pill className="ml-2" data-testid="pill">
        Groceries
      </Pill>,
    );
    expect(screen.getByTestId("pill")).toHaveClass("ml-2");
  });
});

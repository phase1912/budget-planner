import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { IconTile } from "./IconTile";

describe("IconTile", () => {
  it("renders with default classes", () => {
    render(<IconTile data-testid="tile">Icon</IconTile>);
    const tile = screen.getByTestId("tile");
    expect(tile).toHaveClass("bg-muted");
    expect(tile).toHaveClass("w-[34px]");
  });

  it("renders with tone classes", () => {
    render(
      <IconTile tone="error" data-testid="tile">
        Icon
      </IconTile>,
    );
    const tile = screen.getByTestId("tile");
    expect(tile).toHaveClass("bg-tone-error-bg");
    expect(tile).toHaveClass("text-tone-error-text");
  });

  it("renders with size classes", () => {
    render(
      <IconTile size="lg" data-testid="tile">
        Icon
      </IconTile>,
    );
    const tile = screen.getByTestId("tile");
    expect(tile).toHaveClass("w-[40px]");
    expect(tile).toHaveClass("rounded-control");
  });
});

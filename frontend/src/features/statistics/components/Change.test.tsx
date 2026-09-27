import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Change } from "./Change";

describe("Change", () => {
  it("reads spending down in the primary tone, as the design prints it", () => {
    render(<Change change="-69.80" percent="-8.6" />);
    expect(screen.getByText("−69.80 · −8.6%")).toHaveClass("text-primary");
  });

  it("reads spending up in the error tone", () => {
    render(<Change change="88.00" percent="29.5" />);
    expect(screen.getByText("+88.00 · +29.5%")).toHaveClass("text-error");
  });

  it("calls a category with nothing spent before new, not a percentage", () => {
    render(<Change change="20.00" percent={null} />);
    expect(screen.getByText("+20.00 · new")).toBeInTheDocument();
  });

  it("says no change when nothing moved", () => {
    render(<Change change="0" percent="0" />);
    expect(screen.getByText("no change")).toBeInTheDocument();
  });
});

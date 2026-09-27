import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SegmentedControl } from "./SegmentedControl";

const options = [
  { value: "a", label: "Needs review", badge: 3 },
  { value: "b", label: "All items" },
] as const;

describe("SegmentedControl", () => {
  it("marks the current option as pressed and shows its badge", () => {
    render(<SegmentedControl label="View" options={[...options]} value="a" onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /needs review/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "All items" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("reports the chosen option", () => {
    const onChange = vi.fn();
    render(<SegmentedControl label="View" options={[...options]} value="a" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "All items" }));
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("keeps the full label and count as the name when a phone shows a short one", () => {
    render(
      <SegmentedControl
        label="Which items to show"
        value="review"
        onChange={vi.fn()}
        options={[
          { value: "review", label: "Needs review", shortLabel: "To review", badge: 7 },
          { value: "all", label: "All items" },
        ]}
      />,
    );
    expect(screen.getByRole("button", { name: "Needs review 7" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "All items" })).toBeInTheDocument();
  });
});

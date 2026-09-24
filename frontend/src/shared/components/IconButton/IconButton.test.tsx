import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IconButton } from "./IconButton";

describe("IconButton", () => {
  it("is a named, non-submitting button", () => {
    const onClick = vi.fn();
    render(
      <form>
        <IconButton aria-label="Rename Pets" onClick={onClick}>
          ✎
        </IconButton>
      </form>,
    );
    const button = screen.getByRole("button", { name: "Rename Pets" });
    expect(button).toHaveAttribute("type", "button");
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalled();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "./Pagination";

describe("Pagination", () => {
  it("says which slice is shown and moves between pages", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={2} pages={7} size={20} total={132} onPageChange={onPageChange} />);

    expect(screen.getByText("21–40 of 132")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it("cannot go past either end", () => {
    render(<Pagination page={1} pages={1} size={20} total={3} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByText("1–3 of 3")).toBeInTheDocument();
  });
});

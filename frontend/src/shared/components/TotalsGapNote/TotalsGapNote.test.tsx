import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TotalsGapNote } from "./TotalsGapNote";

describe("TotalsGapNote", () => {
  it("names the missed discount and adds exactly that amount", () => {
    const onAddDiscount = vi.fn();
    render(<TotalsGapNote linesSum={226.26} printedTotal={188.02} onAddDiscount={onAddDiscount} />);

    expect(screen.getByText(/Most likely a discount was not read/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add a −38.24 discount" }));
    expect(onAddDiscount).toHaveBeenCalledWith(38.24);
  });

  it("does not offer a discount when the lines come to less than was paid", () => {
    const onFix = vi.fn();
    render(
      <TotalsGapNote
        linesSum={10.88}
        printedTotal={188.02}
        onAddDiscount={vi.fn()}
        onFix={onFix}
      />,
    );

    expect(screen.getByText(/A line is missing or misread/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /discount/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Fix the receipt" }));
    expect(onFix).toHaveBeenCalled();
  });

  it("says nothing when the lines agree within a grosz", () => {
    const { container } = render(<TotalsGapNote linesSum={188.03} printedTotal={188.02} />);

    expect(container).toBeEmptyDOMElement();
  });
});

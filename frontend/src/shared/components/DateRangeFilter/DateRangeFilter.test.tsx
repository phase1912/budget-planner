import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DateRangeFilter } from "./DateRangeFilter";

describe("DateRangeFilter", () => {
  it("hands back whole days, both included, with no time of day", () => {
    const onApply = vi.fn();
    render(<DateRangeFilter start={undefined} end={undefined} onApply={onApply} />);
    fireEvent.click(screen.getByRole("button", { name: "All dates" }));
    const picker = screen.getByRole("dialog");
    fireEvent.change(within(picker).getByRole("combobox"), { target: { value: "month" } });
    fireEvent.change(within(picker).getByLabelText("Month"), { target: { value: "2028-02" } });
    fireEvent.click(within(picker).getByRole("button", { name: "Apply filter" }));

    expect(onApply).toHaveBeenCalledWith("2028-02-01", "2028-02-29");
  });

  it("offers no 'All dates' where a period is always needed", () => {
    render(
      <DateRangeFilter
        start="2026-07-01"
        end="2026-07-27"
        label="1 – 27 Jul 2026"
        allowAll={false}
        onApply={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "1 – 27 Jul 2026" }));
    const options = within(screen.getByRole("dialog")).getAllByRole("option");
    expect(options.map((o) => o.textContent)).not.toContain("All dates");
  });
});

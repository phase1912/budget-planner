import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DateFilterModal } from "./DateFilterModal";
import { StoreProvider } from "../../../stores/StoreContext";
import { RootStore } from "../../../stores/RootStore";

describe("DateFilterModal", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    localStorage.clear();
    rootStore = new RootStore();
  });

  const renderComponent = () =>
    render(
      <StoreProvider store={rootStore}>
        <DateFilterModal />
      </StoreProvider>,
    );

  it("opens on the current month, with three months, all and custom on offer", () => {
    renderComponent();

    expect(screen.getByRole("button", { name: "This month" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: "All time" }));
    expect(rootStore.receiptStore.startDateFilter).toBeUndefined();

    fireEvent.click(screen.getByRole("button", { name: "Custom" }));
    expect(screen.getByText("Filter by date")).toBeInTheDocument();
  });

  it("applies specific date filter", () => {
    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: "Custom" }));

    // Change mode to Specific date
    fireEvent.change(screen.getByLabelText(/Mode/i), { target: { value: "date" } });

    // Set date
    const dateInput = screen.getByLabelText("Date");
    fireEvent.change(dateInput, { target: { value: "2025-05-10" } });

    fireEvent.click(screen.getByRole("button", { name: /Apply filter/i }));

    expect(rootStore.receiptStore.startDateFilter).toBe("2025-05-10");
    expect(rootStore.receiptStore.endDateFilter).toBe("2025-05-10");
    expect(screen.getByRole("button", { name: /10 May 2025/ })).toBeInTheDocument();
  });
});

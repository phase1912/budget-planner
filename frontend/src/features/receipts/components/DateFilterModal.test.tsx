import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DateFilterModal } from "./DateFilterModal";
import { StoreProvider } from "../../../stores/StoreContext";
import { RootStore } from "../../../stores/RootStore";

describe("DateFilterModal", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
  });

  const renderComponent = () =>
    render(
      <StoreProvider store={rootStore}>
        <DateFilterModal />
      </StoreProvider>,
    );

  it("renders correctly and opens modal", () => {
    renderComponent();
    const btn = screen.getByRole("button", { name: /All dates/i });
    expect(btn).toBeInTheDocument();

    fireEvent.click(btn);
    expect(screen.getByText("Filter by date")).toBeInTheDocument();
  });

  it("applies specific date filter", () => {
    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: /All dates/i }));

    // Change mode to Specific date
    fireEvent.change(screen.getByLabelText(/Mode/i), { target: { value: "date" } });

    // Set date
    const dateInput = screen.getByLabelText("Date");
    fireEvent.change(dateInput, { target: { value: "2025-05-10" } });

    fireEvent.click(screen.getByRole("button", { name: /Apply filter/i }));

    expect(rootStore.receiptStore.startDateFilter).toBe("2025-05-10T00:00:00Z");
    expect(rootStore.receiptStore.endDateFilter).toBe("2025-05-10T23:59:59Z");
  });
});

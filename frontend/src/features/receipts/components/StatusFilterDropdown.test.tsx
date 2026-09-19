import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusFilterDropdown } from "./StatusFilterDropdown";
import { StoreProvider } from "../../../stores/StoreContext";
import { RootStore } from "../../../stores/RootStore";

describe("StatusFilterDropdown", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
  });

  const renderComponent = () =>
    render(
      <StoreProvider store={rootStore}>
        <StatusFilterDropdown />
      </StoreProvider>,
    );

  it("renders correctly and opens dropdown", () => {
    renderComponent();
    const btn = screen.getByRole("button", { name: /Any status/i });
    expect(btn).toBeInTheDocument();

    fireEvent.click(btn);
    expect(screen.getByRole("option", { name: /Parsed/i })).toBeInTheDocument();
  });

  it("applies status filter", () => {
    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: /Any status/i }));

    fireEvent.click(screen.getByRole("option", { name: /Parsed/i }));

    expect(rootStore.receiptStore.statusFilter).toBe("parsed");
  });
});

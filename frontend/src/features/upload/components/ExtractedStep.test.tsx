import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { ExtractedStep } from "./ExtractedStep";
import { StoreProvider } from "@/stores/StoreContext";
import { RootStore } from "@/stores/RootStore";

// Mock the SecureImage component since it requires API context
vi.mock("@/shared/components", () => ({
  SecureImage: ({ fileId, alt }: { fileId: string; alt: string }) => (
    <img src={`mock-${fileId}`} alt={alt} data-testid="secure-image" />
  ),
}));

describe("ExtractedStep", () => {
  let mockStore: RootStore;

  beforeEach(() => {
    mockStore = new RootStore();

    // Set up default state
    mockStore.uploadStore.fileIds = ["file-1", "file-2"];
    mockStore.uploadStore.lines = [[]]; // 1 receipt line

    // Mock the extracted data
    mockStore.uploadStore.extractedData = {
      merchant_name: "Test Store",
      transaction_date: "2026-08-28",
      receipt_total: "150.00",
      currency: "PLN",
      items_sum_matches_total: true,
      line_items: [
        {
          name: "Item 1",
          quantity: "2",
          unit_price: "25.00",
          total_price: "50.00",
        },
        {
          name: "Item 2",
          quantity: "1",
          unit_price: "100.00",
          total_price: "100.00",
        },
      ],
    };
  });

  const renderComponent = () =>
    render(
      <StoreProvider store={mockStore}>
        <ExtractedStep />
      </StoreProvider>,
    );

  it("should render merchant name and receipt details", () => {
    renderComponent();
    expect(screen.getByText("Test Store")).toBeInTheDocument();
    expect(screen.getByText(/2026-08-28/)).toBeInTheDocument();
    expect(screen.getByText("150.00 PLN")).toBeInTheDocument();
  });

  it("should render line items", () => {
    renderComponent();
    expect(screen.getByText("Item 1")).toBeInTheDocument();
    expect(screen.getByText("Item 2")).toBeInTheDocument();

    // Check quantity and totals
    expect(screen.getByText("50.00")).toBeInTheDocument();
    expect(screen.getAllByText("100.00").length).toBeGreaterThan(0);
  });

  it("should display success message when total matches", () => {
    renderComponent();
    expect(screen.getByText("Matches the printed total")).toBeInTheDocument();
  });

  it("should display warning message when total is missing", () => {
    mockStore.uploadStore.extractedData = {
      ...mockStore.uploadStore.extractedData,
      items_sum_matches_total: null,
      receipt_total: null,
    };
    renderComponent();
    expect(screen.getByText(/Total · unsure/)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("should display error message when total mismatch", () => {
    mockStore.uploadStore.extractedData = {
      ...mockStore.uploadStore.extractedData,
      items_sum_matches_total: false,
    };
    renderComponent();
    expect(screen.getByText(/Lines do not match printed total/)).toBeInTheDocument();
  });

  it("should reset state and handle back button", () => {
    renderComponent();
    const backButton = screen.getByText("Back to photos");
    fireEvent.click(backButton);

    expect(mockStore.uploadStore.extractedData).toBeNull();
  });
});

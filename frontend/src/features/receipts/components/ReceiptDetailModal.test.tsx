import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReceiptDetailModal } from "./ReceiptDetailModal";

const mockClearSelection = vi.fn();

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    receiptStore: {
      isLoadingDetail: false,
      receiptDetail: {
        id: "r1",
        merchant_name: "Tesco",
        transaction_date: "2026-07-20T14:30:00Z",
        total_amount: "45.50",
        status: "parsed",
        file_ids: ["f1", "f2"],
        line_items: [
          {
            id: "i1",
            name: "Milk",
            quantity: "1",
            unit_price: "2.50",
            total_price: "2.50",
            category: { name: "Groceries" },
          },
        ],
      },
      clearSelection: mockClearSelection,
    },
  }),
}));

describe("ReceiptDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders receipt details correctly", () => {
    render(<ReceiptDetailModal />);

    expect(screen.getByText("Tesco")).toBeInTheDocument();
    expect(screen.getByText("Milk")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("45.50")).toBeInTheDocument();
    expect(screen.getByText("2 photos", { exact: false })).toBeInTheDocument();
  });

  it("calls clearSelection on overlay click", () => {
    render(<ReceiptDetailModal />);

    const overlay = screen.getByTestId("backdrop");
    fireEvent.click(overlay);

    expect(mockClearSelection).toHaveBeenCalled();
  });

  it("calls clearSelection on close button click", () => {
    render(<ReceiptDetailModal />);

    const closeButton = screen.getByRole("button", { name: "Close" });
    fireEvent.click(closeButton);

    expect(mockClearSelection).toHaveBeenCalled();
  });
});

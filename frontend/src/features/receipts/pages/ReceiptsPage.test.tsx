import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReceiptsPage } from "./ReceiptsPage";
import { BrowserRouter } from "react-router-dom";

// Mock ReceiptDetailModal to simplify testing
vi.mock("../components/ReceiptDetailModal", () => ({
  ReceiptDetailModal: () => <div data-testid="receipt-detail-modal">Mock Modal</div>,
}));

const mockFetchReceipts = vi.fn();
const mockFetchReceiptDetail = vi.fn();

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    receiptStore: {
      receipts: [
        {
          id: "r1",
          merchant_name: "Tesco",
          transaction_date: "2026-07-20T14:30:00Z",
          total_amount: "45.50",
          status: "parsed",
          line_items: [{}, {}],
        },
        {
          id: "r2",
          merchant_name: "Unknown Merchant",
          transaction_date: null,
          total_amount: null,
          status: "failed",
          line_items: [],
        },
      ],
      total: 2,
      page: 1,
      size: 20,
      pages: 1,
      isLoadingList: false,
      selectedReceiptId: null,
      fetchReceipts: mockFetchReceipts,
      fetchReceiptDetail: mockFetchReceiptDetail,
    },
  }),
}));

describe("ReceiptsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches receipts on mount", () => {
    render(
      <BrowserRouter>
        <ReceiptsPage />
      </BrowserRouter>,
    );

    expect(mockFetchReceipts).toHaveBeenCalledWith(1, 20);
  });

  it("renders the list of receipts", () => {
    render(
      <BrowserRouter>
        <ReceiptsPage />
      </BrowserRouter>,
    );

    expect(screen.getByText("Tesco")).toBeInTheDocument();
    expect(screen.getByText("45.50")).toBeInTheDocument();

    // Fallbacks
    expect(screen.getByText("Unknown Merchant")).toBeInTheDocument();
  });

  it("opens modal on receipt click", () => {
    render(
      <BrowserRouter>
        <ReceiptsPage />
      </BrowserRouter>,
    );

    const tescoRow = screen.getByText("Tesco").closest("button");
    if (tescoRow) fireEvent.click(tescoRow);

    expect(mockFetchReceiptDetail).toHaveBeenCalledWith("r1");
  });
});

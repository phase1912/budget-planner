import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReceiptDetailModal } from "./ReceiptDetailModal";

const mockClearSelection = vi.fn();
const mockKeep = vi.fn();
const mockConfirmDelete = vi.fn();
const mockSetPrivacy = vi.fn();

const PHOTO_RECEIPT = {
  id: "r1",
  user_id: "me",
  is_private: false,
  merchant_name: "Tesco",
  transaction_date: "2026-07-20T14:30:00Z",
  total_amount: "45.50",
  status: "parsed",
  channel: "photo",
  source_reference: null as string | null,
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
};

const detail = vi.hoisted(() => ({
  receipt: {},
  household: null as null | { members: { user_id: string; first_name: string }[] },
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    categoriesStore: {
      isLoading: false,
      assignableBuiltIns: [{ id: "c1", name: "Groceries", is_builtin: true }],
      customCategories: [],
      isUncategorized: () => false,
      ensureCategories: vi.fn(),
      reassignCategory: vi.fn(),
    },
    toastStore: { showError: vi.fn() },
    authStore: { user: { id: "me", currency: "PLN" } },
    householdStore: {
      get household() {
        return detail.household;
      },
    },
    receiptStore: {
      isLoadingDetail: false,
      get receiptDetail() {
        return detail.receipt;
      },
      clearSelection: mockClearSelection,
      keepPossibleDuplicate: mockKeep,
      confirmDelete: mockConfirmDelete,
      isKeepingDuplicate: false,
      isSavingPrivacy: false,
      setPrivacy: mockSetPrivacy,
    },
  }),
}));

describe("ReceiptDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    detail.receipt = { ...PHOTO_RECEIPT };
    detail.household = null;
  });

  it("renders receipt details correctly", () => {
    render(<ReceiptDetailModal />);

    expect(screen.getByText("Tesco")).toBeInTheDocument();
    expect(screen.getByText("Milk")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("45.50")).toBeInTheDocument();
    expect(screen.getByText("Added from 2 photos", { exact: false })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /photos/i })).toBeInTheDocument();
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

  it("says a receipt came by email, names its message, and offers no photos it lacks", () => {
    detail.receipt = {
      ...PHOTO_RECEIPT,
      channel: "email",
      source_reference: "<receipt-1@shop.example>",
      file_ids: [],
    };
    render(<ReceiptDetailModal />);

    expect(screen.getByText("Added from email", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Reference: receipt-1@shop.example")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /photos/i })).toBeNull();
  });

  it("shows the fiscal numbers that identify the receipt (F11.3)", () => {
    detail.receipt = {
      ...PHOTO_RECEIPT,
      fiscal_register_id: "ECA2201079960",
      fiscal_receipt_number: "85503",
    };
    render(<ReceiptDetailModal />);

    expect(screen.getByText("Register ECA2201079960 · receipt 85503")).toBeInTheDocument();
  });

  it("asks about a likely duplicate and lets the user keep both or remove it (F11.5)", () => {
    detail.receipt = { ...PHOTO_RECEIPT, possible_duplicate_of_id: "r0" };
    render(<ReceiptDetailModal />);

    fireEvent.click(screen.getByRole("button", { name: "Keep both" }));
    fireEvent.click(screen.getByRole("button", { name: /remove/i }));

    expect(mockKeep).toHaveBeenCalled();
    expect(mockConfirmDelete).toHaveBeenCalledWith("r1");
  });

  it("does not ask about duplicates for an ordinary receipt", () => {
    render(<ReceiptDetailModal />);

    expect(screen.queryByRole("button", { name: "Keep both" })).not.toBeInTheDocument();
  });

  it("shows both amounts of a receipt converted from another currency (F11.7)", () => {
    detail.receipt = {
      ...PHOTO_RECEIPT,
      total_amount: "103.42",
      original_currency: "UAH",
      original_total: "1197.00",
      exchange_rate: "0.0864",
      exchange_rate_date: "2026-10-02",
      exchange_rate_source: "NBP",
    };
    render(<ReceiptDetailModal />);

    expect(screen.getByText("1197.00 UAH ≈ 103.42 PLN · NBP rate, 2 October")).toBeInTheDocument();
  });

  it("says why a foreign receipt with no rate is not counted", () => {
    detail.receipt = {
      ...PHOTO_RECEIPT,
      status: "manual_review",
      original_currency: "UAH",
      original_total: "45.50",
      exchange_rate: null,
    };
    render(<ReceiptDetailModal />);

    expect(screen.getByText(/No UAH rate could be found/)).toBeInTheDocument();
  });

  describe("in a household (F12.4)", () => {
    beforeEach(() => {
      detail.household = {
        members: [
          { user_id: "me", first_name: "Bohdan" },
          { user_id: "anna", first_name: "Anna" },
        ],
      };
    });

    it("opens another member's receipt to read, with nothing to change", () => {
      detail.receipt = { ...PHOTO_RECEIPT, user_id: "anna", possible_duplicate_of_id: "r0" };
      render(<ReceiptDetailModal />);

      expect(screen.getByText(/Added by Anna/)).toBeInTheDocument();
      expect(screen.getByText("Groceries")).toBeInTheDocument();
      for (const name of [/Edit/, /Delete/, /photos/i, /Re-run/, "Keep both", "Private"]) {
        expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
      }
      expect(screen.queryByLabelText("Private")).not.toBeInTheDocument();
    });

    it("lets the owner mark their receipt private", () => {
      render(<ReceiptDetailModal />);

      fireEvent.click(screen.getByLabelText("Private"));

      expect(mockSetPrivacy).toHaveBeenCalledWith(true);
    });
  });

  it("offers no privacy outside a household", () => {
    render(<ReceiptDetailModal />);

    expect(screen.queryByLabelText("Private")).not.toBeInTheDocument();
  });
});

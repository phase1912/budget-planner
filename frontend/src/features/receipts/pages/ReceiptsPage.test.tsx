import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReceiptsPage } from "./ReceiptsPage";
import { BrowserRouter, MemoryRouter } from "react-router-dom";

// Mock ReceiptDetailModal to simplify testing
vi.mock("../components/ReceiptDetailModal", () => ({
  ReceiptDetailModal: () => <div data-testid="receipt-detail-modal">Mock Modal</div>,
}));

const mockFetchReceipts = vi.fn();
const mockFetchReceiptDetail = vi.fn();
const mockSetFilters = vi.fn();
const mockStartExport = vi.fn();
const mockSetScope = vi.fn();
const shared = vi.hoisted(() => ({
  household: null as null | { name: string; members: { user_id: string; first_name: string }[] },
  scope: "mine",
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    exportStore: { busy: {}, start: mockStartExport },
    authStore: { user: { id: "me" } },
    householdStore: {
      get household() {
        return shared.household;
      },
      loaded: true,
      load: vi.fn(),
    },
    receiptStore: {
      receipts: [
        {
          id: "r1",
          user_id: "me",
          merchant_name: "Tesco",
          transaction_date: "2026-07-20T14:30:00Z",
          total_amount: "45.50",
          status: "parsed",
          line_items: [{}, {}],
        },
        {
          id: "r2",
          user_id: "anna",
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
      setFilters: mockSetFilters,
      setScope: mockSetScope,
      get scope() {
        return shared.scope;
      },
    },
  }),
}));

describe("ReceiptsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    shared.household = null;
    shared.scope = "mine";
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

  it("opens already narrowed to receipts under review when the dashboard asks", () => {
    render(
      <MemoryRouter initialEntries={["/receipts?status=manual_review"]}>
        <ReceiptsPage />
      </MemoryRouter>,
    );

    expect(mockSetFilters).toHaveBeenCalledWith({ status: "manual_review" });
    expect(mockFetchReceipts).not.toHaveBeenCalled();
  });

  it("ignores a status it does not know", () => {
    render(
      <MemoryRouter initialEntries={["/receipts?status=bogus"]}>
        <ReceiptsPage />
      </MemoryRouter>,
    );

    expect(mockSetFilters).not.toHaveBeenCalled();
    expect(mockFetchReceipts).toHaveBeenCalled();
  });

  it("opens on one month's receipts when the dashboard's All link asks", () => {
    render(
      <MemoryRouter initialEntries={["/receipts?start=2026-08-01&end=2026-08-31"]}>
        <ReceiptsPage />
      </MemoryRouter>,
    );

    expect(mockSetFilters).toHaveBeenCalledWith({
      status: undefined,
      startDate: "2026-08-01",
      endDate: "2026-08-31",
    });
  });

  it("ignores a date range that is not two calendar days", () => {
    render(
      <MemoryRouter initialEntries={["/receipts?start=yesterday&end=2026-08-31"]}>
        <ReceiptsPage />
      </MemoryRouter>,
    );

    expect(mockSetFilters).not.toHaveBeenCalled();
  });

  it("exports the list as filtered on screen, in the format picked", () => {
    render(
      <MemoryRouter>
        <ReceiptsPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Export this list" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /CSV/ }));

    expect(mockStartExport).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "receipts", format: "csv", compare: false }),
    );
  });

  describe("in a household (F12.4)", () => {
    beforeEach(() => {
      shared.household = {
        name: "Home",
        members: [
          { user_id: "me", first_name: "Bohdan" },
          { user_id: "anna", first_name: "Anna" },
        ],
      };
    });

    it("offers a switch between my receipts and the household's", () => {
      render(
        <BrowserRouter>
          <ReceiptsPage />
        </BrowserRouter>,
      );

      fireEvent.click(screen.getByRole("button", { name: "Home" }));

      expect(mockSetScope).toHaveBeenCalledWith("household");
    });

    it("names who added another member's receipt, and drops the export", () => {
      shared.scope = "household";
      render(
        <BrowserRouter>
          <ReceiptsPage />
        </BrowserRouter>,
      );

      expect(screen.getByText("Anna")).toBeInTheDocument();
      expect(screen.queryByText("Bohdan")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Export/ })).not.toBeInTheDocument();
    });
  });

  it("shows no switch outside a household", () => {
    render(
      <BrowserRouter>
        <ReceiptsPage />
      </BrowserRouter>,
    );

    expect(screen.queryByRole("group", { name: "Whose receipts" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mine" })).not.toBeInTheDocument();
  });
});

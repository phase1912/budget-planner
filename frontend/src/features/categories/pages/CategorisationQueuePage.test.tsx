import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";

import type { ItemView, ReviewQueueItem } from "@/stores/CategoriesStore";
import { CategorisationQueuePage } from "./CategorisationQueuePage";

const mockFetchReviewQueue = vi.fn();

const queueItem: ReviewQueueItem = {
  id: "item-1",
  receipt_id: "receipt-1",
  name: "Protein Bar XL",
  quantity: "1",
  unit_price: "20.70",
  total_price: "20.70",
  category_id: "cat-uncat",
  category: { id: "cat-uncat", name: "Uncategorized" },
  category_confidence: 40,
  category_is_low_confidence: true,
  is_category_manual: false,
  merchant_name: "Fresh Market",
  transaction_date: "2026-07-20T14:32:00Z",
};

const mockStore = {
  categoriesStore: {
    reviewQueue: [] as ReviewQueueItem[],
    isLoadingQueue: false,
    queueError: null as string | null,
    fetchReviewQueue: mockFetchReviewQueue,
    queueView: "needs_review" as ItemView,
    queueSearch: "",
    queueStartDate: undefined as string | undefined,
    queueEndDate: undefined as string | undefined,
    queuePage: 1,
    queuePages: 0,
    queueTotal: 0,
    queueSize: 20,
    setQueueDates: vi.fn(),
    setQueuePage: vi.fn(),
    needsReviewCount: 0,
    setQueueView: vi.fn(),
    setQueueSearch: vi.fn(),
    isLoading: false,
    assignableBuiltIns: [],
    customCategories: [],
    isUncategorized: () => true,
    ensureCategories: vi.fn(),
    reassignCategory: vi.fn(),
  },
  toastStore: { showError: vi.fn() },
};

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => mockStore,
}));

function renderPage() {
  render(
    <BrowserRouter>
      <CategorisationQueuePage />
    </BrowserRouter>,
  );
}

describe("CategorisationQueuePage", () => {
  beforeEach(() => {
    mockStore.categoriesStore.reviewQueue = [];
    mockStore.categoriesStore.isLoadingQueue = false;
    mockStore.categoriesStore.queueError = null;
    mockStore.categoriesStore.queueView = "needs_review";
    mockStore.categoriesStore.queueSearch = "";
    mockStore.categoriesStore.needsReviewCount = 0;
    mockStore.categoriesStore.queueTotal = 0;
    mockStore.categoriesStore.queuePages = 0;
    mockStore.categoriesStore.queuePage = 1;
  });

  it("fetches the review queue on mount", () => {
    renderPage();
    expect(mockFetchReviewQueue).toHaveBeenCalled();
  });

  it("lists each waiting item with its merchant, date and amount", () => {
    mockStore.categoriesStore.reviewQueue = [queueItem];
    renderPage();
    expect(screen.getByText("Protein Bar XL")).toBeInTheDocument();
    expect(screen.getByText("Fresh Market")).toBeInTheDocument();
    expect(screen.getByText("20 Jul")).toBeInTheDocument();
    expect(screen.getByText("20.70")).toBeInTheDocument();
    expect(screen.getByLabelText("Category for Protein Bar XL")).toHaveDisplayValue(
      "Uncategorized",
    );
  });

  it("reports a failed load instead of claiming the queue is empty", () => {
    mockStore.categoriesStore.queueError = "Server unavailable";
    renderPage();
    expect(screen.getByText("Server unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Nothing needs review")).not.toBeInTheDocument();
  });

  it("says so when nothing needs review", () => {
    renderPage();
    expect(screen.getByText("Nothing needs review")).toBeInTheDocument();
  });

  it("links to the taxonomy screen", () => {
    renderPage();
    expect(screen.getByRole("link", { name: /manage the taxonomy/i })).toHaveAttribute(
      "href",
      "/categories/manage",
    );
  });

  it("shows how many items wait for review and switches views on request", () => {
    mockStore.categoriesStore.needsReviewCount = 6;
    renderPage();
    const needsReview = screen.getByRole("button", { name: /needs review/i });
    expect(needsReview).toHaveAttribute("aria-pressed", "true");
    expect(needsReview).toHaveTextContent("6");

    fireEvent.click(screen.getByRole("button", { name: "Corrected by you" }));
    expect(mockStore.categoriesStore.setQueueView).toHaveBeenCalledWith("corrected");
  });

  it("explains an empty view in its own terms", () => {
    mockStore.categoriesStore.queueView = "corrected";
    renderPage();
    expect(screen.getByText("No corrections yet")).toBeInTheDocument();
  });

  it("passes the search on to the store", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Find an item"), { target: { value: "bar" } });
    expect(mockStore.categoriesStore.setQueueSearch).toHaveBeenCalledWith("bar");
  });

  it("pages through a long view", () => {
    mockStore.categoriesStore.reviewQueue = [queueItem];
    mockStore.categoriesStore.queueTotal = 45;
    mockStore.categoriesStore.queuePages = 3;
    mockStore.categoriesStore.queuePage = 2;
    renderPage();

    expect(screen.getByText("21–40 of 45")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(mockStore.categoriesStore.setQueuePage).toHaveBeenCalledWith(3);
  });

  it("filters the view by purchase date", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /All dates/i }));
    fireEvent.change(screen.getByLabelText("Mode"), { target: { value: "month" } });
    fireEvent.change(screen.getByLabelText("Month"), { target: { value: "2026-07" } });
    fireEvent.click(screen.getByRole("button", { name: /Apply filter/i }));

    expect(mockStore.categoriesStore.setQueueDates).toHaveBeenCalledWith(
      "2026-07-01T00:00:00Z",
      "2026-07-31T23:59:59Z",
    );
  });
});

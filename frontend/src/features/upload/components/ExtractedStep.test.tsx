import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { ExtractedStep } from "./ExtractedStep";
import { StoreProvider } from "@/stores/StoreContext";
import { RootStore } from "@/stores/RootStore";
import { runInAction } from "mobx";

vi.mock("@/shared/components", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/shared/components")>();
  return {
    ...actual,
    SecureImage: ({ fileId, alt }: { fileId: string; alt: string }) => (
      <img src={`mock-${fileId}`} alt={alt} data-testid="secure-image" />
    ),
  };
});

describe("ExtractedStep", () => {
  let mockStore: RootStore;

  beforeEach(() => {
    mockStore = new RootStore();

    runInAction(() => {
      // Set up default state
      mockStore.uploadStore.fileIds = ["file-1", "file-2"];
      mockStore.uploadStore.lines = [[]]; // 1 receipt line

      // Mock the extracted data
      mockStore.uploadStore.extractedData = {
        extractions: [
          {
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
          },
        ],
      };
    });
  });

  const renderComponent = () =>
    render(
      <StoreProvider store={mockStore}>
        <MemoryRouter>
          <ExtractedStep />
        </MemoryRouter>
      </StoreProvider>,
    );

  it("should render merchant name and receipt details", () => {
    renderComponent();
    expect(screen.getByText("Test Store")).toBeInTheDocument();
    expect(screen.getByText(/2026-08-28/)).toBeInTheDocument();
    expect(screen.getByText("150.00 PLN")).toBeInTheDocument();
  });

  const withConversion = (conversion: Record<string, unknown>) => {
    runInAction(() => {
      const payload = mockStore.uploadStore.extractedData as {
        extractions: Record<string, unknown>[];
      };
      const [extraction = {}] = payload.extractions;
      Object.assign(extraction, { currency: "UAH", receipt_total: "1197.00", conversion });
    });
  };

  it("shows what a foreign receipt will count as before it is stored (F11.7)", () => {
    withConversion({
      currency: "UAH",
      account_currency: "PLN",
      rate: "0.0864",
      rate_date: "2026-10-02",
      source: "NBP",
    });
    renderComponent();
    expect(screen.getByText("1197.00 UAH ≈ 103.42 PLN · NBP rate, 2 October")).toBeInTheDocument();
  });

  it("warns that a foreign receipt with no rate will wait in review", () => {
    withConversion({ currency: "UAH", account_currency: "PLN", unavailable: true });
    renderComponent();
    expect(screen.getByText(/No UAH to PLN rate could be found/)).toBeInTheDocument();
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
    runInAction(() => {
      mockStore.uploadStore.extractedData = {
        extractions: [
          {
            ...(mockStore.uploadStore.extractedData as { extractions: Record<string, unknown>[] })
              .extractions[0],
            items_sum_matches_total: null,
            receipt_total: null,
          },
        ],
      };
    });
    renderComponent();
    expect(screen.getByText(/Total · unsure/)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("should display error message when total mismatch", () => {
    runInAction(() => {
      mockStore.uploadStore.extractedData = {
        extractions: [
          {
            ...(mockStore.uploadStore.extractedData as { extractions: Record<string, unknown>[] })
              .extractions[0],
            items_sum_matches_total: false,
          },
        ],
      };
    });
    renderComponent();
    expect(screen.getByText(/Lines do not match printed total/)).toBeInTheDocument();
  });

  function withExtraction(overrides: Record<string, unknown>) {
    runInAction(() => {
      mockStore.uploadStore.extractedData = {
        extractions: [
          {
            ...(mockStore.uploadStore.extractedData as { extractions: Record<string, unknown>[] })
              .extractions[0],
            ...overrides,
          },
        ],
      };
    });
  }

  it("says only the total is missing when the date was read", () => {
    withExtraction({ requires_manual_review: true, receipt_total: null, computed_total: "150.00" });
    renderComponent();
    expect(screen.getByText("Test Store needs you")).toBeInTheDocument();
    expect(screen.getByText(/^No total could be read/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enter the total" })).toBeInTheDocument();
  });

  it("opens the total form with the lines' sum offered and prefilled", () => {
    withExtraction({ requires_manual_review: true, receipt_total: null, computed_total: "150.00" });
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: "Enter the total" }));

    const field = screen.getByLabelText("Printed total");
    expect(field).toHaveValue("150.00");
    expect(field).toHaveFocus();
    expect(screen.getByRole("button", { name: "150.00 is right" })).toBeInTheDocument();
  });

  it("accepting the lines' sum saves it as the total", () => {
    const resolveTotal = vi.spyOn(mockStore.uploadStore, "resolveTotal").mockResolvedValue(true);
    withExtraction({ requires_manual_review: true, receipt_total: null, computed_total: "150.00" });
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: "Enter the total" }));
    fireEvent.click(screen.getByRole("button", { name: "150.00 is right" }));

    expect(resolveTotal).toHaveBeenCalledWith(0, "150.00");
  });

  it("will not save something that is not an amount", () => {
    withExtraction({ requires_manual_review: true, receipt_total: null, computed_total: "150.00" });
    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: "Enter the total" }));

    fireEvent.change(screen.getByLabelText("Printed total"), { target: { value: "abc" } });
    expect(screen.getByText("Enter a number, e.g. 37.00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save total" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Printed total"), { target: { value: "37,00" } });
    expect(screen.getByRole("button", { name: "Save total" })).toBeEnabled();
  });

  it("offers no total form when only the date is missing", () => {
    withExtraction({ requires_manual_review: true, transaction_date: null });
    renderComponent();
    expect(screen.getByText(/^No date could be read/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enter the total" })).not.toBeInTheDocument();
  });

  it("should reset state and handle back button", () => {
    renderComponent();
    const backButton = screen.getByText("Back to photos");
    fireEvent.click(backButton);

    expect(mockStore.uploadStore.extractedData).toBeNull();
  });

  it("shows an OPUST discount beside the line it was folded into", () => {
    withExtraction({
      line_items: [
        {
          name: "Olej 3l",
          quantity: "2",
          unit_price: "16.99",
          total_price: "23.94",
          discount: "10.04",
        },
      ],
    });
    renderComponent();
    expect(screen.getByText("23.94")).toBeInTheDocument();
    expect(screen.getByText("incl. −10.04 off")).toBeInTheDocument();
  });

  it("asks nothing about storing a receipt when it is the only one", () => {
    renderComponent();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("lets one of several receipts be left out, and says so in words", () => {
    runInAction(() => {
      const [first] = (mockStore.uploadStore.extractedData as { extractions: object[] })
        .extractions;
      mockStore.uploadStore.extractedData = {
        extractions: [first, { ...first, merchant_name: "Second Store" }],
      };
      mockStore.uploadStore.selectedIndices = new Set([0, 1]);
    });
    renderComponent();

    const boxes = screen.getAllByRole("checkbox", { name: "Save this receipt" });
    expect(boxes).toHaveLength(2);
    const [, second] = boxes;
    if (!second) throw new Error("expected two receipts");
    fireEvent.click(second);
    expect(screen.getByRole("checkbox", { name: "Leave this receipt out" })).not.toBeChecked();
  });

  it("says the app already tried before asking about a gap it could not close", () => {
    withExtraction({
      items_sum_matches_total: false,
      computed_total: "153.00",
      total_reconciled_by: "unresolved",
    });
    renderComponent();
    expect(screen.getByText(/We read this receipt again and still could not/)).toBeInTheDocument();
  });

  it("says an undated receipt took its upload day, and offers to change it", () => {
    withExtraction({ transaction_date: "2026-10-09", transaction_date_assumed: true });
    renderComponent();

    expect(screen.getByText(/No date on the receipt/)).toHaveTextContent("9 October 2026");
    fireEvent.click(screen.getByRole("button", { name: "Change date" }));
    expect(mockStore.uploadStore.editingExtractionIndex).toBe(0);
  });
});

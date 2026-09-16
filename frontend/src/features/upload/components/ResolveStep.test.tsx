import { render, screen, fireEvent } from "@testing-library/react";

import { describe, it, expect, beforeEach } from "vitest";
import { ResolveStep } from "./ResolveStep";
import { StoreProvider } from "@/stores/StoreContext";
import { RootStore } from "@/stores/RootStore";
import { runInAction } from "mobx";

describe("ResolveStep", () => {
  let mockStore: RootStore;

  beforeEach(() => {
    mockStore = new RootStore();
  });

  const renderComponent = () =>
    render(
      <StoreProvider store={mockStore}>
        <ResolveStep />
      </StoreProvider>,
    );

  it("should render 'Comparison not possible' error panel for not_possible matches", () => {
    runInAction(() => {
      mockStore.uploadStore.currentStep = 3;
      mockStore.uploadStore.extractedData = {
        extractions: [
          {
            merchant_name: "Test Store",
            currency: "PLN",
            line_items: [
              {
                name: "Bananas",
                quantity: "1",
                unit_price: "3.20",
                total_price: "3.20",
              },
              {
                name: "Bananas",
                quantity: "1",
                unit_price: "3.20",
                total_price: "3.20",
              },
            ],
            position_matches: [
              {
                item_a_index: 0,
                item_b_index: 1,
                result: "not_possible",
                reason: "Photo 2 failed to parse",
              },
            ],
          },
        ],
      };
    });

    renderComponent();

    // The header of the card
    expect(screen.getByText("“Bananas” appears in both photos")).toBeInTheDocument();

    // The specific 'Comparison not possible' error text
    expect(screen.getByText("Comparison not possible")).toBeInTheDocument();

    // The reason from the backend
    expect(screen.getByText("Photo 2 failed to parse")).toBeInTheDocument();
  });

  it("should render standard conflict card for 'same' matches", () => {
    runInAction(() => {
      mockStore.uploadStore.currentStep = 3;
      mockStore.uploadStore.extractedData = {
        extractions: [
          {
            merchant_name: "Test Store",
            currency: "PLN",
            line_items: [
              {
                name: "Milk",
                quantity: "1",
                unit_price: "4.50",
                total_price: "4.50",
              },
              {
                name: "Milk",
                quantity: "1",
                unit_price: "4.50",
                total_price: "4.50",
              },
            ],
            position_matches: [
              {
                item_a_index: 0,
                item_b_index: 1,
                result: "same",
              },
            ],
          },
        ],
      };
    });

    renderComponent();

    expect(screen.getByText("“Milk” kept as one purchase")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Change"));
    expect(screen.getByText("“Milk” appears in both photos")).toBeInTheDocument();
    expect(screen.getByText("One item, counted once")).toBeInTheDocument();
    expect(screen.getByText("Two items, counted twice")).toBeInTheDocument();
  });
});

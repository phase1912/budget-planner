import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CategoriesPage } from "./CategoriesPage";
import { BrowserRouter } from "react-router-dom";

const mockFetchCategories = vi.fn();

const mockStore = {
  categoriesStore: {
    isLoading: false,
    error: null as string | null,
    builtInCategories: [
      {
        id: "1",
        name: "Groceries",
        is_builtin: true,
        item_count: 5,
        total_amount: "150.00",
      },
      {
        id: "2",
        name: "Uncategorized",
        is_builtin: true,
        item_count: 2,
        total_amount: "20.00",
      },
    ],
    customCategories: [
      {
        id: "3",
        name: "Hobbies",
        is_builtin: false,
        item_count: 1,
        total_amount: "50.00",
      },
    ],
    fetchCategories: mockFetchCategories,
  },
};

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => mockStore,
}));

describe("CategoriesPage", () => {
  it("fetches categories on mount", () => {
    render(
      <BrowserRouter>
        <CategoriesPage />
      </BrowserRouter>,
    );
    expect(mockFetchCategories).toHaveBeenCalled();
  });

  it("renders loading state", () => {
    mockStore.categoriesStore.isLoading = true;
    render(
      <BrowserRouter>
        <CategoriesPage />
      </BrowserRouter>,
    );
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    mockStore.categoriesStore.isLoading = false;
  });

  it("renders error state", () => {
    mockStore.categoriesStore.error = "Network Error";
    render(
      <BrowserRouter>
        <CategoriesPage />
      </BrowserRouter>,
    );
    expect(screen.getByText("Network Error")).toBeInTheDocument();
    mockStore.categoriesStore.error = null;
  });

  it("renders built-in and custom categories with correct counts and totals", () => {
    render(
      <BrowserRouter>
        <CategoriesPage />
      </BrowserRouter>,
    );

    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("5 items · 150.00 PLN")).toBeInTheDocument();

    expect(screen.getByText("Uncategorized")).toBeInTheDocument();
    expect(screen.getByText("2 items · awaiting your review")).toBeInTheDocument();

    expect(screen.getByText("Hobbies")).toBeInTheDocument();
    expect(screen.getByText("1 items · 50.00 PLN")).toBeInTheDocument();
  });
});

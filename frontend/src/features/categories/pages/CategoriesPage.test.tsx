import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";

import type { Category } from "@/stores/CategoriesStore";
import { CategoriesPage } from "./CategoriesPage";

const groceries: Category = {
  id: "1",
  name: "Groceries",
  is_builtin: true,
  item_count: 5,
  total_amount: "150.00",
};
const other: Category = {
  id: "4",
  name: "Other",
  is_builtin: true,
  item_count: 0,
  total_amount: "0",
};
const uncategorized: Category = {
  id: "2",
  name: "Uncategorized",
  is_builtin: true,
  item_count: 2,
  total_amount: "20.00",
};
const pets: Category = {
  id: "3",
  name: "Pet Supplies",
  is_builtin: false,
  item_count: 1,
  total_amount: "50.00",
};

const store = {
  isLoading: false,
  error: null as string | null,
  categories: [groceries, other, uncategorized, pets],
  builtInCategories: [groceries, other, uncategorized],
  customCategories: [pets],
  fetchCategories: vi.fn(),
  createCategory: vi.fn<(name: string) => Promise<string | null>>(),
  renameCategory: vi.fn<(id: string, name: string) => Promise<string | null>>(),
  deleteCategory: vi.fn<(id: string, moveToId: string) => Promise<string | null>>(),
};
const showError = vi.fn();

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({ categoriesStore: store, toastStore: { showError } }),
}));

function renderPage() {
  render(
    <BrowserRouter>
      <CategoriesPage />
    </BrowserRouter>,
  );
}

describe("CategoriesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    store.isLoading = false;
    store.error = null;
  });

  it("fetches categories on mount and lists built-ins with their totals", () => {
    renderPage();
    expect(store.fetchCategories).toHaveBeenCalled();
    expect(screen.getByText("5 items · 150.00 PLN")).toBeInTheDocument();
    expect(screen.getByText("2 items · awaiting your review")).toBeInTheDocument();
    expect(screen.getByText("1 item · 50.00 PLN")).toBeInTheDocument();
  });

  it("shows loading until the first list arrives", () => {
    store.isLoading = true;
    const loaded = store.categories;
    store.categories = [];
    renderPage();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    store.categories = loaded;
  });

  it("renders error state", () => {
    store.error = "Failed to load";
    renderPage();
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
  });

  it("offers rename and delete only on the user's own categories", () => {
    renderPage();
    expect(screen.getByRole("button", { name: "Rename Pet Supplies" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Delete Pet Supplies" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Rename Groceries" })).not.toBeInTheDocument();
  });

  it("creates a category from a trimmed name in a dialog", async () => {
    store.createCategory.mockResolvedValue(null);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "New category" }));
    const dialog = screen.getByRole("dialog", { name: "New category" });
    const name = within(dialog).getByLabelText("Name");
    expect(name).toHaveFocus();
    expect(within(dialog).getByRole("button", { name: "Create category" })).toBeDisabled();

    fireEvent.change(name, { target: { value: "  Kids & school " } });
    fireEvent.submit(name);

    expect(store.createCategory).toHaveBeenCalledWith("Kids & school");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("explains a refused name beside the field and keeps what was typed", async () => {
    store.createCategory.mockResolvedValue("A category named “Groceries” already exists.");
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "New category" }));
    const dialog = screen.getByRole("dialog", { name: "New category" });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Groceries" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create category" }));

    expect(
      await within(dialog).findByText("A category named “Groceries” already exists."),
    ).toBeVisible();
    expect(within(dialog).getByLabelText("Name")).toHaveValue("Groceries");
  });

  it("closes the dialog without creating anything on cancel", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "New category" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(store.createCategory).not.toHaveBeenCalled();
  });

  it("renames in place", async () => {
    store.renameCategory.mockResolvedValue(null);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Rename Pet Supplies" }));
    fireEvent.change(screen.getByLabelText("New name for Pet Supplies"), {
      target: { value: "Pets" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save the new name" }));

    expect(store.renameCategory).toHaveBeenCalledWith("3", "Pets");
    await waitFor(() => {
      expect(screen.queryByLabelText("New name for Pet Supplies")).not.toBeInTheDocument();
    });
  });

  it("asks where the items go before deleting, defaulting to Other", async () => {
    store.deleteCategory.mockResolvedValue(null);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Delete Pet Supplies" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/1 item is filed under it, worth 50.00 PLN/)).toBeVisible();
    const target = within(dialog).getByLabelText("Move those items to");
    expect(target).toHaveDisplayValue("Other");
    expect(within(target).queryByRole("option", { name: "Pet Supplies" })).toBeNull();

    fireEvent.click(within(dialog).getByRole("button", { name: "Delete and move" }));

    expect(store.deleteCategory).toHaveBeenCalledWith("3", "4");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });
});

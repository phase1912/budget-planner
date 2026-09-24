import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InlineCategoryPicker } from "./InlineCategoryPicker";

const reassignCategory = vi.fn<(itemId: string, categoryId: string) => Promise<string | null>>();
const ensureCategories = vi.fn();
const showError = vi.fn();

const groceries = { id: "c-groceries", name: "Groceries", is_builtin: true };
const health = { id: "c-health", name: "Health", is_builtin: true };
const uncategorized = { id: "c-uncat", name: "Uncategorized", is_builtin: true };
const pets = { id: "c-pets", name: "Pet Supplies", is_builtin: false };

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    categoriesStore: {
      isLoading: false,
      assignableBuiltIns: [groceries, health],
      customCategories: [pets],
      isUncategorized: (id: string | null | undefined) => !id || id === uncategorized.id,
      ensureCategories,
      reassignCategory,
    },
    toastStore: { showError },
  }),
}));

function renderPicker(currentCategoryId: string | null, onCategoryChanged = vi.fn()) {
  render(
    <InlineCategoryPicker
      itemId="item-1"
      itemName="Protein Bar XL"
      currentCategoryId={currentCategoryId}
      onCategoryChanged={onCategoryChanged}
    />,
  );
  return { picker: screen.getByLabelText("Category for Protein Bar XL"), onCategoryChanged };
}

describe("InlineCategoryPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows an Uncategorized item as awaiting a decision, without offering Uncategorized", () => {
    const { picker } = renderPicker(uncategorized.id);
    expect(picker).toHaveDisplayValue("Uncategorized");
    expect(picker).toHaveClass("border-tone-warning-border");
    expect(screen.getByRole("option", { name: "Uncategorized" })).toBeDisabled();
    expect(screen.getByRole("option", { name: "Pet Supplies" })).toBeInTheDocument();
    expect(ensureCategories).toHaveBeenCalled();
  });

  it("reassigns the item and tells the parent to refresh", async () => {
    reassignCategory.mockResolvedValue(null);
    const { picker, onCategoryChanged } = renderPicker(uncategorized.id);

    fireEvent.change(picker, { target: { value: health.id } });

    expect(reassignCategory).toHaveBeenCalledWith("item-1", health.id);
    await waitFor(() => {
      expect(onCategoryChanged).toHaveBeenCalled();
    });
  });

  it("tells the user when the change is refused, and leaves the list alone", async () => {
    reassignCategory.mockResolvedValue("Category not found");
    const { picker, onCategoryChanged } = renderPicker(groceries.id);

    fireEvent.change(picker, { target: { value: health.id } });

    await waitFor(() => {
      expect(showError).toHaveBeenCalledWith("Category not found");
    });
    expect(onCategoryChanged).not.toHaveBeenCalled();
  });
});

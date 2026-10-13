import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Product } from "@/stores/ProductsStore";
import { ProductsPage } from "./ProductsPage";

const YOGHURT: Product = {
  id: "p1",
  name: "Jogurt Natural 330ml",
  size_amount: "330",
  size_unit: "ml",
  purchases: 9,
  shops: 2,
  last_bought: "2026-10-12T10:00:00Z",
  spent: "42.41",
  variants: [
    { alias_id: "a1", printed_name: "Jogurt Natural 330ml", purchases: 6 },
    { alias_id: "a2", printed_name: "JOG NAT 330ML", purchases: 3 },
  ],
};
const BREAD: Product = {
  ...YOGHURT,
  id: "p2",
  name: "Chleb 300g",
  size_amount: "300",
  size_unit: "g",
  purchases: 1,
  shops: 1,
  variants: [{ alias_id: "a3", printed_name: "Chleb 300g", purchases: 1 }],
};

const store = vi.hoisted(() => ({
  products: [] as unknown[],
  search: "",
  selected: [] as string[],
  isLoading: false,
  isSaving: false,
  loadError: null as string | null,
  get selectedProducts() {
    return store.products.filter((p) => store.selected.includes((p as { id: string }).id));
  },
  load: vi.fn(),
  setSearch: vi.fn(),
  toggle: vi.fn((id: string) => {
    store.selected = store.selected.includes(id)
      ? store.selected.filter((s) => s !== id)
      : [...store.selected, id];
  }),
  clearSelection: vi.fn(),
  merge: vi.fn().mockResolvedValue(true),
  split: vi.fn(),
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({ productsStore: store, authStore: { user: { currency: "PLN" } } }),
}));

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/statistics/products"]}>
      <ProductsPage />
    </MemoryRouter>,
  );

describe("ProductsPage (F16.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    store.products = [YOGHURT, BREAD];
    store.selected = [];
  });

  it("lists each product once, with how often, where and how it was printed", () => {
    renderPage();

    expect(screen.getByRole("link", { name: "Products" })).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("checkbox", { name: "Select Jogurt Natural 330ml" }),
    ).toBeInTheDocument();
    expect(screen.getByText("330 ml")).toBeInTheDocument();
    expect(screen.getByText(/bought 9 times · 2 shops/)).toBeInTheDocument();
    expect(screen.getAllByText("42.41 PLN")).toHaveLength(2);
    expect(screen.getByText("How receipts print it (2)")).toBeInTheDocument();
  });

  it("splits a wrongly joined way of printing off its product", () => {
    renderPage();

    fireEvent.click(
      screen.getByRole("button", { name: "Make “JOG NAT 330ML” a product of its own" }),
    );

    expect(store.split).toHaveBeenCalledWith("p1", "a2");
    // A product printed one way has nothing to split.
    expect(screen.queryByRole("button", { name: /Chleb 300g.*own/ })).not.toBeInTheDocument();
  });

  it("merges the ticked products under the name the user keeps", async () => {
    store.selected = ["p1", "p2"];
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Merge" }));
    fireEvent.click(screen.getByRole("radio", { name: "Chleb 300g" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Merge" }));

    await vi.waitFor(() => {
      expect(store.merge).toHaveBeenCalledWith("p2");
    });
  });
});

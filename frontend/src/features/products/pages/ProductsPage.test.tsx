import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Exploration } from "@/stores/ExplorationStore";
import type { Product } from "@/stores/ProductsStore";
import { ExplorePage } from "./ExplorePage";
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
  productById: (id: string) => store.products.find((p) => (p as { id: string }).id === id),
  load: vi.fn(),
  loadOverview: vi.fn(),
  overview: null,
  setSearch: vi.fn(),
  toggle: vi.fn((id: string) => {
    store.selected = store.selected.includes(id)
      ? store.selected.filter((s) => s !== id)
      : [...store.selected, id];
  }),
  clearSelection: vi.fn(),
  merge: vi.fn().mockResolvedValue(true),
  split: vi.fn(),
  select: vi.fn((ids: string[]) => {
    store.selected = [...ids];
  }),
}));

const exploration = vi.hoisted(() => ({
  productIds: [] as string[],
  preset: "this_month",
  start: "2026-10-01",
  end: "2026-10-31",
  result: null as Exploration | null,
  isLoading: false,
  error: null as string | null,
  selections: [] as { id: string; name: string; product_ids: string[] }[],
  isSaving: false,
  setProducts: vi.fn(),
  loadSelections: vi.fn(),
  choosePreset: vi.fn(),
  chooseRange: vi.fn(),
  saveSelection: vi.fn().mockResolvedValue(true),
  deleteSelection: vi.fn(),
  selectionMatching: (ids: readonly string[]) =>
    exploration.selections.find(
      (selection) =>
        selection.product_ids.length === new Set(ids).size &&
        selection.product_ids.every((id) => ids.includes(id)),
    ),
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    productsStore: store,
    explorationStore: exploration,
    authStore: { user: { currency: "PLN" } },
  }),
}));

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/statistics/products"]}>
      <ProductsPage />
    </MemoryRouter>,
  );

const renderExplore = () =>
  render(
    <MemoryRouter initialEntries={["/products/explore"]}>
      <ExplorePage />
    </MemoryRouter>,
  );

describe("ProductsPage (F16.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    store.products = [YOGHURT, BREAD];
    store.selected = [];
    exploration.result = null;
    exploration.selections = [];
  });

  it("lists each product once, with how often, where and how it was printed", () => {
    renderPage();

    expect(
      screen.getByRole("checkbox", { name: "Select Jogurt Natural 330ml" }),
    ).toBeInTheDocument();
    expect(screen.getByText("330 ml")).toBeInTheDocument();
    expect(screen.getByText(/bought 9 times · 2 shops/)).toBeInTheDocument();
    expect(screen.getAllByText("42.41 PLN")).toHaveLength(2);
    expect(screen.getByText("How receipts print it (2)")).toBeInTheDocument();
  });

  it("says where a product recently cost less than where it was last bought (F16.3)", () => {
    store.products = [
      {
        ...YOGHURT,
        cheaper: { shop: "Lidl", instead_of: "Biedronka", difference: "1.52", percent: "9.1" },
      },
      BREAD,
    ];
    renderPage();

    expect(
      screen.getByText("Cheaper at Lidl: 1.52 PLN/piece less (9%) than at Biedronka"),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Cheaper at/)).toHaveLength(1);
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

  it("leads to exploring what is ticked from a bar that stays in view", () => {
    store.selected = ["p1", "p2"];
    renderPage();

    expect(screen.getByRole("link", { name: /2 products selected.*Explore/ })).toHaveAttribute(
      "href",
      "/products/explore",
    );
  });

  it("merges the ticked products under the name the user keeps", async () => {
    store.selected = ["p1", "p2"];
    renderExplore();

    fireEvent.click(screen.getByRole("button", { name: "Merge" }));
    fireEvent.click(screen.getByRole("radio", { name: "Chleb 300g" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Merge" }));

    await vi.waitFor(() => {
      expect(store.merge).toHaveBeenCalledWith("p2");
    });
  });

  it("explores what is ticked: amounts, prices per shop and the change (F16.2)", () => {
    store.selected = ["p1"];
    exploration.result = {
      totals: { times: 3, spent: "14.97", quantities: { g: "990.000" } },
      months: [
        {
          month: "2026-09-01",
          amounts: { times: 1, spent: "4.49", quantities: {} },
          by_product: [{ product_id: "p1", spent: "4.49" }],
        },
        {
          month: "2026-10-01",
          amounts: { times: 2, spent: "10.48", quantities: {} },
          by_product: [{ product_id: "p1", spent: "10.48" }],
        },
      ],
      products: [
        {
          product: YOGHURT,
          amounts: { times: 3, spent: "14.97", quantities: { g: "990.000" } },
          prices: [
            { day: "2026-09-02", shop: "Lidl", unit_price: "4.49", base_price: "13.61" },
            { day: "2026-10-02", shop: "Biedronka", unit_price: "4.99", base_price: "15.12" },
            { day: "2026-10-05", shop: "Lidl", unit_price: "5.49", base_price: "16.64" },
          ],
          change: { first: "13.61", last: "16.64", difference: "3.03", percent: "22.3" },
          shops: [
            {
              shop: "Biedronka",
              purchases: 1,
              average: "15.12",
              latest: "15.12",
              latest_day: "2026-10-02",
              above_cheapest: "0.00",
              above_percent: "0.0",
            },
            {
              shop: "Lidl",
              purchases: 2,
              average: "15.13",
              latest: "16.64",
              latest_day: "2026-10-05",
              above_cheapest: "1.52",
              above_percent: "10.1",
            },
          ],
        },
      ],
    };
    renderExplore();

    expect(exploration.setProducts).toHaveBeenCalledWith(["p1"]);
    expect(screen.getAllByText(/990 g/).length).toBeGreaterThan(0);
    expect(screen.getByText("3×")).toBeInTheDocument();
    expect(
      screen.getByText("Price per l went from 13.61 to 16.64 PLN (+22.3%)."),
    ).toBeInTheDocument();
    const shops = screen.getByRole("list", { name: "Prices of Jogurt Natural 330ml by shop" });
    expect(within(shops).getByText("Cheapest")).toBeInTheDocument();
    expect(within(shops).getByText("+1.52 PLN (10.1%)")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "By month" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /October 2026: 10.48 PLN/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("figure")).toBeInTheDocument();
  });

  it("opens a saved selection and saves the ticked products as a new one (F16.2)", async () => {
    exploration.selections = [{ id: "s1", name: "Snacks", product_ids: ["p1", "p2"] }];
    store.selected = ["p1"];
    renderExplore();

    fireEvent.click(screen.getByRole("button", { name: "Snacks" }));
    expect(store.select).toHaveBeenCalledWith(["p1", "p2"]);

    fireEvent.click(screen.getByRole("button", { name: "Save set" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Breakfast" } });
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(exploration.saveSelection).toHaveBeenCalledWith("Breakfast");
    });
  });

  it("does not offer to save a saved selection again once it is open", () => {
    exploration.selections = [{ id: "s1", name: "Snacks", product_ids: ["p1", "p2"] }];
    store.selected = ["p2", "p1"];
    renderExplore();

    expect(screen.getByRole("button", { name: "Snacks" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Snacks" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save set" })).not.toBeInTheDocument();
  });

  it("says why a product bought once has no price chart", () => {
    store.products = [YOGHURT];
    store.selected = ["p1"];
    exploration.result = {
      totals: { times: 1, spent: "4.49", quantities: {} },
      months: [
        {
          month: "2026-10-01",
          amounts: { times: 1, spent: "4.49", quantities: {} },
          by_product: [{ product_id: "p1", spent: "4.49" }],
        },
      ],
      products: [
        {
          product: YOGHURT,
          amounts: { times: 1, spent: "4.49", quantities: {} },
          prices: [{ day: "2026-10-02", shop: "Lidl", unit_price: "4.49", base_price: "13.61" }],
          change: null,
          shops: [],
        },
      ],
    };
    renderExplore();

    expect(
      screen.getByText(
        "Bought once in this period: the price chart appears from the second purchase.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("figure")).not.toBeInTheDocument();
  });
});

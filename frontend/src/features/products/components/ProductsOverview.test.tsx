import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ProductsOverview } from "./ProductsOverview";

const stores = vi.hoisted(() => ({
  productsStore: {
    products: [{ id: "bread", name: "Bread", purchases: 14, spent: "90.86" }],
    select: vi.fn(),
    overview: {
      moves: [
        {
          product: { id: "milk", name: "Milk 1 l", size_amount: null, size_unit: null },
          change: { first: "3.49", last: "3.99", difference: "0.50", percent: "14.3" },
          last_shop: "Biedronka",
          history: ["3.49", "3.79", "3.99"],
          shops: [
            { shop: "Lidl", latest: "3.79" },
            { shop: "Biedronka", latest: "3.99" },
            { shop: "Żabka", latest: "4.69" },
          ],
        },
      ],
      shops: [
        { shop: "Lidl", cheapest_for: 7, paid_above: "0" },
        { shop: "Żabka", cheapest_for: 1, paid_above: "38.20" },
      ],
      paid_above: "38.20",
    },
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

describe("ProductsOverview (F23.5)", () => {
  it("names the price that moved, says where it costs what, and opens it for exploring", () => {
    render(<ProductsOverview currency="PLN" />, { wrapper: MemoryRouter });

    expect(screen.getByText("Biedronka · 3.49 → 3.99 PLN")).toBeInTheDocument();
    expect(screen.getByText("+14%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Milk 1 l/ }));
    expect(screen.getByText("Where it costs what")).toBeInTheDocument();
    expect(screen.getByText("Lidl")).toBeInTheDocument();
    expect(screen.getByText("4.69 PLN")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /See it month by month/ }));
    expect(stores.productsStore.select).toHaveBeenCalledWith(["milk"]);
  });

  it("ranks the shops and says what was paid above the cheapest", () => {
    render(<ProductsOverview currency="PLN" />, { wrapper: MemoryRouter });
    const [bestShop] = screen.getAllByRole("button", { name: /Best shop/ });
    if (!bestShop) throw new Error("no Best shop tab");
    fireEvent.click(bestShop);

    expect(screen.getByText(/About 38 PLN paid above the cheapest shop/)).toBeInTheDocument();
    expect(screen.getByText("cheapest for 7 products")).toBeInTheDocument();
  });

  it("lists what is bought most", () => {
    render(<ProductsOverview currency="PLN" />, { wrapper: MemoryRouter });
    fireEvent.click(screen.getByRole("button", { name: /Bought most/ }));
    expect(screen.getByText("×14")).toBeInTheDocument();
  });
});

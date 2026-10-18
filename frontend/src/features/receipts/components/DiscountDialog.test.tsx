import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DiscountDialog } from "./DiscountDialog";

const stores = vi.hoisted(() => ({
  receiptStore: {
    isSavingDiscount: false,
    setDiscount: vi.fn().mockResolvedValue(true),
    receiptDetail: {
      total_amount: "169.00",
      paid_discount: null as string | null,
      line_items: [
        { id: "coffee", name: "Coffee", total_price: "119.00" },
        { id: "shirt", name: "T-shirt", total_price: "50.00" },
      ],
    },
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

describe("DiscountDialog (F23.7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.receiptStore.receiptDetail.paid_discount = null;
  });

  it("takes the discount off the whole receipt and shows what was paid", async () => {
    const onClose = vi.fn();
    render(<DiscountDialog onClose={onClose} />);

    fireEvent.change(screen.getByLabelText("Not paid"), { target: { value: "100" } });
    expect(screen.getByText("69.00")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await vi.waitFor(() => {
      expect(stores.receiptStore.setDiscount).toHaveBeenCalledWith("100", null);
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("narrows it to the ticked lines only when asked, and refuses more than they cost", () => {
    render(<DiscountDialog onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Only on some items" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /T-shirt/ }));
    fireEvent.change(screen.getByLabelText("Not paid"), { target: { value: "60" } });
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Not paid"), { target: { value: "20" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(stores.receiptStore.setDiscount).toHaveBeenCalledWith("20", ["shirt"]);
  });

  it("removes a discount already there", () => {
    stores.receiptStore.receiptDetail.paid_discount = "100.00";
    render(<DiscountDialog onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Remove the discount" }));
    expect(stores.receiptStore.setDiscount).toHaveBeenCalledWith(null);
  });
});

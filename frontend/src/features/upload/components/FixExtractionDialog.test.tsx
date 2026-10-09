import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { runInAction } from "mobx";
import { describe, expect, it, vi } from "vitest";

import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { FixExtractionDialog } from "./FixExtractionDialog";

function open(extraction: Record<string, unknown>) {
  const store = new RootStore();
  runInAction(() => {
    store.uploadStore.extractedData = { extractions: [extraction] };
    store.uploadStore.editingExtractionIndex = 0;
  });
  const resolveDate = vi.spyOn(store.uploadStore, "resolveDate");
  render(
    <StoreProvider store={store}>
      <FixExtractionDialog />
    </StoreProvider>,
  );
  return { resolveDate };
}

describe("FixExtractionDialog", () => {
  it("sets the purchase date of a receipt that showed none", async () => {
    const { resolveDate } = open({
      merchant_name: "McDonald's",
      transaction_date: "2026-10-09",
      transaction_date_assumed: true,
      line_items: [],
    });
    expect(screen.getByText(/Not on the receipt/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Purchase date"), { target: { value: "2026-10-03" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(resolveDate).toHaveBeenCalledWith(0, "2026-10-03");
    });
  });

  it("leaves a date read off the receipt alone when it is not changed", async () => {
    const { resolveDate } = open({ transaction_date: "2026-10-03", line_items: [] });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(resolveDate).not.toHaveBeenCalled();
    });
  });
});

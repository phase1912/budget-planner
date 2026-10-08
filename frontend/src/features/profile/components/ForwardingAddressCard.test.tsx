import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { ForwardingAddressCard } from "./ForwardingAddressCard";

describe("ForwardingAddressCard", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
    rootStore.authStore.user = {
      id: "uuid",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      currency: "USD",
      budget_limit: null,
      forwarding_address: "receipts-ab12@inbound.test",
    };
  });

  const renderCard = () =>
    render(
      <StoreProvider store={rootStore}>
        <ForwardingAddressCard />
      </StoreProvider>,
    );

  it("shows the address and copies it", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    renderCard();

    expect(screen.getByText("receipts-ab12@inbound.test")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy address" }));

    expect(writeText).toHaveBeenCalledWith("receipts-ab12@inbound.test");
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("asks before replacing the address, and replaces it only on confirmation", async () => {
    const regenerate = vi
      .spyOn(rootStore.profileStore, "regenerateForwardingAddress")
      .mockResolvedValue(true);
    renderCard();

    fireEvent.click(screen.getByRole("button", { name: "Get a new address" }));
    expect(screen.getByText(/stops working at once/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Keep it" }));
    expect(regenerate).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Get a new address" }));
    fireEvent.click(screen.getByRole("button", { name: "Replace address" }));

    await waitFor(() => {
      expect(regenerate).toHaveBeenCalledTimes(1);
    });
    expect(await screen.findByRole("button", { name: "Get a new address" })).toBeInTheDocument();
  });
});

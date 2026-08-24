import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ProfilePage } from "./ProfilePage";
import { StoreProvider } from "@/stores/StoreContext";
import { RootStore } from "@/stores/RootStore";

describe("ProfilePage", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
    rootStore.authStore.user = {
      id: "uuid",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      currency: "USD",
      budget_limit: "1000",
    };

    // Stub api client on profileStore
    vi.spyOn(rootStore.profileStore, "updateProfile").mockResolvedValue(true);
  });

  it("renders with user preferences", () => {
    render(
      <StoreProvider store={rootStore}>
        <ProfilePage />
      </StoreProvider>,
    );

    expect(screen.getByText("Preferences")).toBeInTheDocument();

    // Currency is a select box if no receipts, or locked if receipts
    // Since receiptCount is 0, it should be a select box
    const currencySelect = screen.getByLabelText("Currency");
    expect(currencySelect).toHaveValue("USD");

    const budgetInput = screen.getByLabelText("Monthly budget limit");
    expect(budgetInput).toHaveAttribute("value", "1000");
  });

  it("calls updateProfile on save", async () => {
    render(
      <StoreProvider store={rootStore}>
        <ProfilePage />
      </StoreProvider>,
    );

    const budgetInput = screen.getByLabelText("Monthly budget limit");
    fireEvent.change(budgetInput, { target: { value: "2000" } });

    const currencySelect = screen.getByLabelText("Currency");
    fireEvent.change(currencySelect, { target: { value: "EUR" } });

    const saveButton = screen.getByRole("button", { name: "Save preferences" });
    fireEvent.click(saveButton);

    await waitFor(() => {
      // eslint-disable-next-line @typescript-eslint/unbound-method
      expect(rootStore.profileStore.updateProfile).toHaveBeenCalledWith({
        currency: "EUR",
        budget_limit: 2000,
      });
    });
  });

  it("allows removing the budget limit", () => {
    render(
      <StoreProvider store={rootStore}>
        <ProfilePage />
      </StoreProvider>,
    );

    const removeBtn = screen.getByRole("button", { name: "Remove the limit" });
    fireEvent.click(removeBtn);

    const budgetInput = screen.getByLabelText("Monthly budget limit");
    expect(budgetInput).toHaveValue(null);
  });
});

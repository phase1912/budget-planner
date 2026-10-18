import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
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
      forwarding_address: "receipts-test@example.com",
      email_confirmed: true,
      is_admin: false,
      is_super_admin: false,
      two_factor_enabled: false,
      dark_at_night: false,
      travels_for_work: false,
      pays_own_taxes: false,
    };

    // Stub api client on profileStore
    vi.spyOn(rootStore.profileStore, "updateProfile").mockResolvedValue(true);
    vi.spyOn(rootStore.profileStore, "loadProfile").mockResolvedValue();
  });

  const renderPage = () =>
    render(
      <StoreProvider store={rootStore}>
        <MemoryRouter>
          <ProfilePage />
        </MemoryRouter>
      </StoreProvider>,
    );

  it("shows the account's settings as rows, money among them", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Currency/ })).toHaveTextContent("USD");
    expect(screen.getByRole("button", { name: /Monthly budget limit/ })).toHaveTextContent(
      "1,000 USD",
    );
  });

  it("changes the currency and the payday from their rows", async () => {
    const save = vi.spyOn(rootStore.profileStore, "saveQuietly").mockResolvedValue(true);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Currency/ }));
    fireEvent.change(screen.getByRole("combobox", { name: "Currency" }), {
      target: { value: "EUR" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      // eslint-disable-next-line @typescript-eslint/unbound-method
      expect(rootStore.profileStore.updateProfile).toHaveBeenCalledWith({ currency: "EUR" });
    });

    fireEvent.click(screen.getByRole("button", { name: /Payday/ }));
    fireEvent.change(screen.getByRole("combobox", { name: "Payday" }), { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(save).toHaveBeenCalledWith({ payday: 10 });
    });
  });

  it("paints a palette at once and keeps it on the account (F23.1)", () => {
    const choose = vi.spyOn(rootStore.profileStore, "choosePalette").mockResolvedValue();
    renderPage();

    fireEvent.click(screen.getByRole("radio", { name: /Rose/ }));

    expect(choose).toHaveBeenCalledWith("rose");
  });

  it("shows business trips only to someone who travels for work (F23.12)", () => {
    const save = vi.spyOn(rootStore.profileStore, "saveQuietly").mockResolvedValue(true);
    renderPage();

    expect(screen.queryByRole("link", { name: "Open business trips" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("switch", { name: "I travel for work" }));
    expect(save).toHaveBeenCalledWith({ travels_for_work: true });
  });
});

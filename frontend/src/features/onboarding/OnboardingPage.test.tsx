import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { OnboardingPage } from "./OnboardingPage";
import { StoreProvider } from "@/stores/StoreContext";
import { RootStore } from "@/stores/RootStore";

describe("OnboardingPage", () => {
  let rootStore: RootStore;
  let finish: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    rootStore = new RootStore();
    rootStore.authStore.user = {
      id: "uuid",
      email: "new@example.com",
      first_name: "New",
      last_name: "User",
      currency: "EUR",
      budget_limit: null,
      email_confirmed: true,
      is_admin: false,
      is_super_admin: false,
      two_factor_enabled: false,
      dark_at_night: false,
      travels_for_work: false,
      pays_own_taxes: false,
      onboarded_at: null,
      forwarding_address: "receipts-new@example.com",
    };
    finish = vi.spyOn(rootStore.profileStore, "finishOnboarding").mockResolvedValue(true);
  });

  const renderPage = () =>
    render(
      <StoreProvider store={rootStore}>
        <MemoryRouter initialEntries={["/welcome"]}>
          <Routes>
            <Route path="/welcome" element={<OnboardingPage />} />
            <Route path="/" element={<p>home</p>} />
            <Route path="/upload" element={<p>upload</p>} />
          </Routes>
        </MemoryRouter>
      </StoreProvider>,
    );

  const next = () => {
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  };

  it("walks through the steps and saves what was chosen, then opens the upload", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Set up in a minute" }));
    expect(screen.getByRole("button", { name: "EUR" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "PLN" }));
    next();
    fireEvent.click(screen.getByRole("radio", { name: /Rose/ }));
    expect(rootStore.themeStore.palette).toBe("rose");
    next();
    // Regular incomes are saved as they are added (F23.17), in the PLN just chosen.
    fireEvent.click(screen.getByRole("button", { name: "Add a regular income" }));
    expect(screen.getByLabelText("A month, PLN")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("On your accounts today"), {
      target: { value: "1 250,50" },
    });
    next();
    next();
    fireEvent.click(screen.getByRole("button", { name: "Add my first receipt" }));

    await waitFor(() => {
      expect(screen.getByText("upload")).toBeInTheDocument();
    });
    expect(finish).toHaveBeenCalledWith(
      expect.objectContaining({
        currency: "PLN",
        palette: "rose",
        starting_balance: "1250.50",
      }),
    );
  });

  it("skipping keeps the defaults and still marks the setup as done", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Use the defaults and start" }));

    await waitFor(() => {
      expect(screen.getByText("home")).toBeInTheDocument();
    });
    expect(finish).toHaveBeenCalledWith({});
  });
});

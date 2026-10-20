import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { apiClient } from "@/api/client";
import { OnboardingPage } from "./OnboardingPage";
import { StoreProvider } from "@/stores/StoreContext";
import { RootStore } from "@/stores/RootStore";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), use: vi.fn() },
}));

type Call = (path: string, options?: { body?: unknown }) => Promise<unknown>;
const api = apiClient as unknown as Record<"GET" | "POST", ReturnType<typeof vi.fn<Call>>>;

const HOME = {
  id: "h1",
  name: "Home",
  my_role: "owner",
  owner_sets_budget: false,
  invite_code: "c0de",
  members: [],
};

/** The accounts the setup opened, by the body each POST carried. */
const opened = () =>
  api.POST.mock.calls.filter(([path]) => path === "/api/v1/accounts").map(([, o]) => o?.body);

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
    vi.clearAllMocks();
    api.GET.mockImplementation((path: string) =>
      Promise.resolve({
        data:
          path === "/api/v1/accounts"
            ? { accounts: [], total: "0", set_aside: "0" }
            : path === "/api/v1/household"
              ? null
              : [],
      }),
    );
    api.POST.mockImplementation((path: string) =>
      Promise.resolve({ data: path === "/api/v1/household" ? HOME : {} }),
    );
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

  it("walks through the steps, opens the purchase card and saves what was chosen", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Set up in a minute" }));
    expect(screen.getByRole("button", { name: "EUR" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "PLN" }));
    next();
    fireEvent.click(screen.getByRole("radio", { name: /Rose/ }));
    expect(rootStore.themeStore.palette).toBe("rose");
    next();
    // The card purchases come off (F23.15), opened as the step is left.
    fireEvent.change(screen.getByLabelText("On it now"), { target: { value: "1 250,50" } });
    next();
    await waitFor(() => {
      expect(opened()).toEqual([
        expect.objectContaining({
          name: "My card",
          kind: "personal",
          opening: "1250.50",
          for_purchases: true,
        }),
      ]);
    });
    // Regular incomes are saved as they are added (F23.17), in the PLN just chosen.
    fireEvent.click(await screen.findByRole("button", { name: "Add a regular income" }));
    expect(screen.getByLabelText("A month, PLN")).toBeInTheDocument();
    next();
    expect(screen.getByRole("radio", { name: /Just me for now/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    next();
    await screen.findByText("Lock it with a code");
    next();
    fireEvent.click(await screen.findByRole("button", { name: "Add my first receipt" }));

    await waitFor(() => {
      expect(screen.getByText("upload")).toBeInTheDocument();
    });
    expect(finish).toHaveBeenCalledWith(
      expect.objectContaining({ currency: "PLN", palette: "rose" }),
    );
  });

  it("opens a business account with its tax when there is one (F23.15)", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Set up in a minute" }));
    next();
    next();

    fireEvent.click(screen.getByRole("switch", { name: /I also have a business account/ }));
    fireEvent.change(screen.getByLabelText("On it now", { selector: "#onboarding-business" }), {
      target: { value: "30000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "12%" }));
    next();

    // No amount on the card: only the business account is opened.
    await waitFor(() => {
      expect(opened()).toEqual([
        expect.objectContaining({ kind: "business", opening: "30000", tax_rate: "12" }),
      ]);
    });
  });

  it("starts a family and shows the link to invite them (E12)", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Set up in a minute" }));
    for (let i = 0; i < 4; i++) {
      next();
      await screen.findByRole("button", { name: "Continue" });
    }

    fireEvent.click(screen.getByRole("radio", { name: /With my family/ }));
    fireEvent.click(screen.getByRole("button", { name: "Start the family" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/household", { body: { name: "Home" } });
    });
    expect(await screen.findByText(/\/join\/c0de/)).toBeInTheDocument();
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

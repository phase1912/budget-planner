import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { JoinHouseholdPage } from "./JoinHouseholdPage";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), use: vi.fn() },
}));

const api = apiClient as unknown as Record<"GET" | "POST", ReturnType<typeof vi.fn>>;

describe("JoinHouseholdPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderPage = () =>
    render(
      <StoreProvider store={new RootStore()}>
        <MemoryRouter initialEntries={["/join/abc123"]}>
          <Routes>
            <Route path="/join/:code" element={<JoinHouseholdPage />} />
            <Route path="/profile" element={<p>Profile page</p>} />
          </Routes>
        </MemoryRouter>
      </StoreProvider>,
    );

  it("says whose household the link leads to before joining", async () => {
    api.GET.mockResolvedValue({ data: { name: "Home", owner_name: "Bohdan R", member_count: 1 } });
    renderPage();

    expect(await screen.findByText("Bohdan R")).toBeInTheDocument();
    expect(api.GET).toHaveBeenCalledWith("/api/v1/household/invites/{code}", {
      params: { path: { code: "abc123" } },
    });
    expect(api.POST).not.toHaveBeenCalled();
  });

  it("joins and goes to Profile", async () => {
    api.GET.mockResolvedValue({ data: { name: "Home", owner_name: "Bohdan R", member_count: 1 } });
    api.POST.mockResolvedValue({
      data: { id: "h1", name: "Home", my_role: "member", members: [], invite_code: null },
    });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Join Home" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/household/join", {
        body: { code: "abc123" },
      });
    });
    expect(await screen.findByText("Profile page")).toBeInTheDocument();
  });

  it("shows why joining was refused", async () => {
    api.GET.mockResolvedValue({ data: { name: "Home", owner_name: "Bohdan R", member_count: 1 } });
    api.POST.mockResolvedValue({
      error: { detail: "This household keeps its budget in PLN and your account is in USD." },
    });
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Join Home" }));

    expect(await screen.findByText(/keeps its budget in PLN/)).toBeInTheDocument();
  });

  it("says a dead link leads nowhere", async () => {
    api.GET.mockResolvedValue({
      error: { detail: "This invite link is not valid. Ask for a new one." },
    });
    renderPage();

    expect(await screen.findByText(/Ask for a new one/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Join/ })).not.toBeInTheDocument();
  });
});

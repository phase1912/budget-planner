import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { RootStore } from "@/stores/RootStore";
import type { Household } from "@/stores/HouseholdStore";
import { StoreProvider } from "@/stores/StoreContext";
import { HouseholdCard } from "./HouseholdCard";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn(), use: vi.fn() },
}));

const api = apiClient as unknown as Record<
  "GET" | "POST" | "PATCH" | "DELETE",
  ReturnType<typeof vi.fn>
>;

const ME = "me-id";
const ANNA = "anna-id";

function household(myRole: "owner" | "member", withAnna = true): Household {
  const members = [
    {
      user_id: ME,
      first_name: "Bohdan",
      last_name: "R",
      email: "me@example.com",
      role: "owner",
      joined_at: "2026-10-09T10:00:00Z",
    },
  ];
  if (withAnna)
    members.push({
      user_id: ANNA,
      first_name: "Anna",
      last_name: "R",
      email: "anna@example.com",
      role: "member",
      joined_at: "2026-10-09T11:00:00Z",
    });
  return { id: "h1", name: "Home", my_role: myRole, members };
}

describe("HouseholdCard", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    vi.clearAllMocks();
    rootStore = new RootStore();
    rootStore.authStore.user = {
      id: ME,
      email: "me@example.com",
      first_name: "Bohdan",
      last_name: "R",
      currency: "PLN",
      budget_limit: null,
      forwarding_address: "x@y",
    };
  });

  const renderCard = () =>
    render(
      <StoreProvider store={rootStore}>
        <HouseholdCard />
      </StoreProvider>,
    );

  it("offers to start a household when the user has none", async () => {
    api.GET.mockResolvedValue({ data: null });
    api.POST.mockResolvedValue({ data: household("owner", false) });
    renderCard();

    fireEvent.change(await screen.findByLabelText("Household name"), {
      target: { value: "  Home " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create household" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/household", { body: { name: "Home" } });
    });
    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
  });

  it("lists the members with their roles and marks the user", async () => {
    api.GET.mockResolvedValue({ data: household("owner") });
    renderCard();

    expect(await screen.findByText("Anna R")).toBeInTheDocument();
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
  });

  it("lets the owner remove a member only after confirming", async () => {
    api.GET.mockResolvedValue({ data: household("owner") });
    api.DELETE.mockResolvedValue({ data: household("owner", false) });
    renderCard();

    fireEvent.click(await screen.findByRole("button", { name: "Remove" }));
    expect(api.DELETE).not.toHaveBeenCalled();
    const dialog = screen.getByRole("alertdialog", { name: "Remove Anna R" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Remove" }));

    await waitFor(() => {
      expect(api.DELETE).toHaveBeenCalledWith("/api/v1/household/members/{user_id}", {
        params: { path: { user_id: ANNA } },
      });
    });
  });

  it("tells an owner with members to remove them before leaving", async () => {
    api.GET.mockResolvedValue({ data: household("owner") });
    renderCard();

    expect(await screen.findByText(/remove the other members first/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Leave household/ })).not.toBeInTheDocument();
  });

  it("lets a member leave, but neither rename nor remove", async () => {
    api.GET.mockResolvedValue({ data: { ...household("member"), my_role: "member" } });
    api.POST.mockResolvedValue({ data: undefined });
    if (rootStore.authStore.user) rootStore.authStore.user.id = ANNA;
    renderCard();

    fireEvent.click(await screen.findByRole("button", { name: "Leave household" }));
    expect(screen.queryByRole("button", { name: "Rename" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Leave" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/household/leave");
    });
    expect(await screen.findByRole("button", { name: "Create household" })).toBeInTheDocument();
  });

  it("lets the owner rename the household", async () => {
    api.GET.mockResolvedValue({ data: household("owner") });
    api.PATCH.mockResolvedValue({ data: { ...household("owner"), name: "Family" } });
    renderCard();

    fireEvent.click(await screen.findByRole("button", { name: "Rename" }));
    fireEvent.change(screen.getByLabelText("Household name"), { target: { value: "Family" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByRole("heading", { name: "Family" })).toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HelpPage } from "./HelpPage";

const stores = vi.hoisted(() => ({
  contactStore: {
    state: { status: "idle", error: null as string | null, isLoading: false },
    send: vi.fn(),
    reset: vi.fn(),
  },
  authStore: { user: { email: "ann@example.com" } },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderHelp = () =>
  render(
    <MemoryRouter initialEntries={["/help"]}>
      <HelpPage />
    </MemoryRouter>,
  );

describe("HelpPage (F17.10)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.contactStore.state = { status: "idle", error: null, isLoading: false };
  });

  it("answers by area, every answer with an address of its own", () => {
    renderHelp();

    const perDiem = screen.getByRole("link", { name: "How is the per diem counted?" });
    expect(perDiem).toHaveAttribute("href", "#trips-perdiem");
    expect(document.getElementById("trips-perdiem")).not.toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Trips and per diem" })).toBeVisible();
    expect(screen.getByText(/in Poland 45 zł a day/)).toBeInTheDocument();
  });

  it("sends a question with the signed-in user's address filled in", () => {
    renderHelp();

    expect(screen.getByLabelText("Your email address")).toHaveValue("ann@example.com");
    expect(screen.getByRole("link", { name: "bohdan.razhyk.support@gmail.com" })).toHaveAttribute(
      "href",
      "mailto:bohdan.razhyk.support@gmail.com",
    );
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "data" } });
    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Please send me everything you keep about me." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(stores.contactStore.send).toHaveBeenCalledWith(
      "ann@example.com",
      "data",
      "Please send me everything you keep about me.",
      "",
    );
  });

  it("says the message went, and offers to write another", () => {
    stores.contactStore.state = { status: "success", error: null, isLoading: false };
    renderHelp();

    expect(screen.getByText(/your message is on its way/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Write another" }));
    expect(stores.contactStore.reset).toHaveBeenCalled();
  });
});

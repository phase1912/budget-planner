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

describe("HelpPage (F17.10, F17.11)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.contactStore.state = { status: "idle", error: null, isLoading: false };
  });

  it("answers by area, every answer with an address of its own and where it lives", () => {
    renderHelp();

    const perDiem = document.getElementById("trips-perdiem");
    expect(perDiem?.tagName).toBe("DETAILS");
    expect(
      screen.getByRole("heading", { level: 3, name: "How is the per diem counted?" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Settings › Regular bills")).toBeInTheDocument();
  });

  it("opens the answer a link points to", () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(
      <MemoryRouter initialEntries={["/help#income-taxes"]}>
        <HelpPage />
      </MemoryRouter>,
    );

    expect(document.getElementById("income-taxes")).toHaveAttribute("open");
  });

  it("finds answers by a word and says when nothing matches", () => {
    renderHelp();

    fireEvent.change(screen.getByLabelText("Search the help"), { target: { value: "rent" } });

    expect(
      screen.getByRole("heading", { level: 2, name: "Answers for “rent”" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Rent and other fixed bills" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3, name: "How do I add a receipt?" })).toBeNull();

    fireEvent.change(screen.getByLabelText("Search the help"), { target: { value: "zebra" } });
    expect(screen.getByText(/Nothing matches “zebra”/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show all" }));
    expect(
      screen.getByRole("heading", { level: 3, name: "How do I add a receipt?" }),
    ).toBeInTheDocument();
  });

  it("narrows the answers to a topic", () => {
    renderHelp();

    fireEvent.click(screen.getByRole("button", { name: /Products/ }));

    expect(screen.getByRole("heading", { level: 2, name: "Products" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "A product has a strange name" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3, name: "I forgot my password" })).toBeNull();
  });

  it("walks through the app in four steps", () => {
    renderHelp();

    fireEvent.click(screen.getByRole("tab", { name: /Plan the month/ }));

    expect(screen.getByRole("tabpanel")).toHaveTextContent(
      "Add your salary and rent once in Plan.",
    );
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

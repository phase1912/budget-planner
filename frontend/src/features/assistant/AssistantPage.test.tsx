import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";
import { isApproval } from "@/shared/speech";
import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { AssistantPage } from "./AssistantPage";

vi.mock("@/api/client", () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), use: vi.fn() },
}));

type Call = (path: string, options?: { body?: unknown }) => Promise<unknown>;
const api = apiClient as unknown as Record<"GET" | "POST", ReturnType<typeof vi.fn<Call>>>;

const CARD = {
  id: "m3",
  role: "assistant",
  text: "",
  card: { kind: "budget", fields: { amount: "2500" } },
  card_state: "proposed",
  saved_ref: null,
  created_at: "2026-10-20T10:00:00Z",
};
const CONVERSATION = {
  id: "c1",
  title: "Raise the budget",
  updated_at: "2026-10-20T10:00:00Z",
  messages: [
    { ...CARD, id: "m1", role: "user", text: "Raise the budget", card: null, card_state: null },
    { ...CARD, id: "m2", text: "Here is the budget card.", card: null, card_state: null },
    CARD,
  ],
};

describe("the assistant (F21.1, F21.7)", () => {
  let store: RootStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new RootStore();
    store.authStore.user = { id: "me", currency: "PLN" } as typeof store.authStore.user;
    api.GET.mockResolvedValue({ data: [] });
    api.POST.mockImplementation((path: string, options) =>
      Promise.resolve({
        data: path.endsWith("/save")
          ? {
              ...CARD,
              card: { kind: "budget", fields: (options?.body as { fields: object }).fields },
              card_state: "saved",
              saved_ref: "plan:budget",
            }
          : CONVERSATION,
      }),
    );
  });

  const renderPage = () =>
    render(
      <StoreProvider store={store}>
        <MemoryRouter>
          <AssistantPage />
        </MemoryRouter>
      </StoreProvider>,
    );

  it("starts with what it can do, and sends an example", async () => {
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Salary came: 9 000 from Acme" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/messages", {
        body: expect.objectContaining({
          text: "Salary came: 9 000 from Acme",
          conversation_id: null,
        }) as unknown,
      });
    });
    expect(await screen.findByText("Here is the budget card.")).toBeInTheDocument();
  });

  it("saves a card only on Approve, with the field as the user changed it", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "Raise the budget" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    const card = await screen.findByRole("article", { name: "Monthly budget" });
    expect(api.POST).not.toHaveBeenCalledWith(
      "/api/v1/assistant/cards/{message_id}/save",
      expect.anything(),
    );

    fireEvent.change(within(card).getByLabelText("Amount, PLN"), { target: { value: "2 600" } });
    fireEvent.click(within(card).getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/cards/{message_id}/save", {
        params: { path: { message_id: "m3" } },
        body: expect.objectContaining({ fields: { amount: "2600" } }) as unknown,
      });
    });
    expect(await within(card).findByText("Saved")).toBeInTheDocument();
  });

  it("clears the field at once and answers messages sent in a row one after another", async () => {
    const answers: ((value: unknown) => void)[] = [];
    api.POST.mockImplementation(
      () =>
        new Promise((resolve) => {
          answers.push(resolve);
        }),
    );
    renderPage();
    const input = screen.getByLabelText("Write a message");

    for (const said of ["Taxi 45", "Coffee 12"]) {
      fireEvent.change(input, { target: { value: said } });
      fireEvent.click(screen.getByRole("button", { name: "Send" }));
      expect(input).toHaveValue("");
    }

    expect(screen.getByText("Taxi 45")).toBeInTheDocument();
    expect(screen.getByText("Coffee 12")).toBeInTheDocument();
    expect(api.POST).toHaveBeenCalledTimes(1);
    act(() => {
      answers[0]?.({ data: CONVERSATION });
    });
    await waitFor(() => {
      expect(api.POST).toHaveBeenLastCalledWith("/api/v1/assistant/messages", {
        body: expect.objectContaining({ text: "Coffee 12", conversation_id: "c1" }) as unknown,
      });
    });
    act(() => {
      answers[1]?.({ data: CONVERSATION });
    });
    await waitFor(() => {
      expect(screen.queryByText("Thinking…")).not.toBeInTheDocument();
    });
  });

  it("saves the waiting card when the user says approve", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "Raise the budget" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByRole("article", { name: "Monthly budget" });

    act(() => {
      store.assistantStore.approveByVoice();
    });

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith(
        "/api/v1/assistant/cards/{message_id}/save",
        expect.anything(),
      );
    });
  });

  it("lets the category of a spoken expense be changed before it is approved (F21.3)", async () => {
    store.categoriesStore.categories = [
      { id: "transport", name: "Transport" },
      { id: "dining", name: "Dining" },
    ] as typeof store.categoriesStore.categories;
    const expense = {
      ...CARD,
      id: "e1",
      card: {
        kind: "expense",
        fields: {
          description: "Coffee",
          amount: "12",
          spent_on: "2026-10-19",
          category_id: "transport",
          currency: null,
        },
      },
    };
    api.POST.mockImplementation((path: string, options) =>
      Promise.resolve({
        data: path.endsWith("/save")
          ? {
              ...expense,
              card_state: "saved",
              saved_ref: "receipt:r1",
              card: { kind: "expense", fields: (options?.body as { fields: object }).fields },
            }
          : { ...CONVERSATION, messages: [CONVERSATION.messages[0], expense] },
      }),
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Yesterday taxi 45, coffee 12" }));
    const card = await screen.findByRole("article", { name: "Spent" });

    fireEvent.change(within(card).getByLabelText("Category"), { target: { value: "dining" } });
    fireEvent.click(within(card).getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/cards/{message_id}/save", {
        params: { path: { message_id: "e1" } },
        body: expect.objectContaining({
          fields: expect.objectContaining({
            category_id: "dining",
            spent_on: "2026-10-19",
          }) as unknown,
        }) as unknown,
      });
    });
  });

  it("hears approve in every language it speaks", () => {
    expect(["Approve.", "підтверджую", "Zatwierdzam!"].map(isApproval)).toEqual([true, true, true]);
    expect(isApproval("approve the budget of 2500")).toBe(false);
  });
});

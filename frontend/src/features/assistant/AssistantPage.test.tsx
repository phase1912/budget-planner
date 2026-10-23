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
vi.mock("@/shared/speech", async (actual) => ({
  ...(await actual<typeof import("@/shared/speech")>()),
  canRecord: () => true,
  record: vi.fn(() =>
    Promise.resolve({
      stop: () => Promise.resolve(new Blob(["RIFF"], { type: "audio/wav" })),
      cancel: vi.fn(),
    }),
  ),
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

  it("reports a reply with its reason, and says it is reported (F22.4.2)", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "Raise the budget" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    fireEvent.click(await screen.findByRole("button", { name: "Report" }));
    fireEvent.click(screen.getByRole("button", { name: "Wrong or misleading" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/messages/{message_id}/report", {
        params: { path: { message_id: "m2" } },
        body: { reason: "wrong" },
      });
    });
    expect(await screen.findByText("Reported, thank you")).toBeInTheDocument();
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

  it("answers a question with the chart and a link to the screen with the same period (F21.4)", async () => {
    const answered = {
      ...CONVERSATION,
      messages: [
        {
          ...CARD,
          id: "q1",
          role: "user",
          text: "Groceries vs last month?",
          card: null,
          card_state: null,
        },
        {
          ...CARD,
          id: "q2",
          text: "Groceries: 100 now, 60 in September.",
          card: null,
          card_state: null,
        },
        {
          ...CARD,
          id: "q3",
          card_state: "shown",
          card: {
            kind: "answer",
            fields: {
              screen: "spending",
              to: "/spending?start=2026-10-01&end=2026-10-31&compare=1",
              start: "2026-10-01",
              end: "2026-10-31",
              previous_start: "2026-09-01",
              previous_end: "2026-09-30",
              chart: {
                scale_max: "100",
                ticks: ["0", "50", "100"],
                hidden: 0,
                groups: [
                  {
                    category_id: null,
                    name: "Groceries",
                    current: { value: "100.00", height: "100" },
                    previous: { value: "60.00", height: "60" },
                  },
                ],
              },
            },
          },
        },
      ],
    };
    api.POST.mockResolvedValue({ data: answered });
    renderPage();

    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "Groceries vs last month?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Groceries: 100 now, 60 in September.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Category by category" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in Spending" })).toHaveAttribute(
      "href",
      "/spending?start=2026-10-01&end=2026-10-31&compare=1",
    );
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("draws a change of any kind from its form and saves it as edited (F21.7.1)", async () => {
    const change = {
      ...CARD,
      id: "c3",
      card: {
        kind: "bill_change",
        fields: {
          bill_id: "b1",
          target: "Gym",
          name: "Gym",
          amount: "60",
          day: null,
          weekday: 0,
        },
        form: [
          { name: "target", kind: "target", options: [], required: true },
          { name: "name", kind: "text", options: [], required: true },
          { name: "amount", kind: "amount", options: [], required: true },
          { name: "repeat", kind: "repeat", options: [], required: true },
        ],
      },
    };
    api.POST.mockImplementation((path: string, options) =>
      Promise.resolve({
        data: path.endsWith("/save")
          ? {
              ...change,
              card: { ...change.card, fields: (options?.body as { fields: object }).fields },
              card_state: "saved",
            }
          : { ...CONVERSATION, messages: [change] },
      }),
    );
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), { target: { value: "gym 70" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    const card = await screen.findByRole("article", { name: "Change a bill" });
    expect(within(card).getByText("Gym", { selector: "p" })).toBeInTheDocument();
    expect(within(card).getByLabelText("Day of the week")).toHaveValue("0");
    fireEvent.change(within(card).getByLabelText("Amount, PLN"), { target: { value: "70" } });
    fireEvent.click(within(card).getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/cards/{message_id}/save", {
        params: { path: { message_id: "c3" } },
        body: expect.objectContaining({
          fields: expect.objectContaining({ amount: "70", weekday: 0 }) as unknown,
        }) as unknown,
      });
    });
    expect(await within(card).findByText("Saved")).toBeInTheDocument();
  });

  it("lets the lines of a told receipt be corrected or taken out before it is approved (F21.8.1)", async () => {
    const told = {
      ...CARD,
      id: "c5",
      card: {
        kind: "told_receipt",
        fields: {
          shop: "Biedronka",
          spent_on: "2026-10-23",
          currency: null,
          lines: [
            { name: "Mleko", quantity: "1", amount: "4" },
            { name: "Chleb", quantity: "1", amount: "5" },
          ],
        },
        form: [
          { name: "shop", kind: "text", options: [], required: true },
          { name: "spent_on", kind: "date", options: [], required: true },
          { name: "lines", kind: "lines", options: [], required: true },
        ],
      },
    };
    api.POST.mockImplementation((path: string, options) =>
      Promise.resolve({
        data: path.endsWith("/save")
          ? {
              ...told,
              card: { ...told.card, fields: (options?.body as { fields: object }).fields },
              card_state: "saved",
            }
          : { ...CONVERSATION, messages: [told] },
      }),
    );
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "Biedronka: milk 4, bread 5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    const card = await screen.findByRole("article", { name: "Told receipt" });
    fireEvent.change(within(card).getByLabelText("Line 1, amount"), { target: { value: "4,29" } });
    fireEvent.click(within(card).getByRole("button", { name: "Take Chleb out" }));
    expect(within(card).getByText("Total 4.29 PLN")).toBeInTheDocument();
    fireEvent.click(within(card).getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/cards/{message_id}/save", {
        params: { path: { message_id: "c5" } },
        body: expect.objectContaining({
          fields: expect.objectContaining({
            lines: [{ name: "Mleko", quantity: "1", amount: "4.29" }],
          }) as unknown,
        }) as unknown,
      });
    });
  });

  it("asks on a balance card how the difference counts, and asks a category only for purchases (F21.10)", async () => {
    store.categoriesStore.categories = [
      { id: "other", name: "Other" },
    ] as typeof store.categoriesStore.categories;
    const balance = {
      ...CARD,
      id: "b1",
      card: {
        kind: "balance",
        fields: {
          account_id: "a1",
          target: "Revolut: 4100.00 → 3700.00 PLN",
          bank_balance: "3700",
          way: null,
          category_id: "other",
          description: "Purchases not entered",
        },
        form: [
          { name: "target", kind: "target", options: [], required: true },
          { name: "bank_balance", kind: "balance", options: [], required: true },
          { name: "way", kind: "choice", options: ["correct", "spending"], required: true },
          { name: "category_id", kind: "category", options: [], required: false },
          { name: "description", kind: "text", options: [], required: true },
        ],
      },
    };
    api.POST.mockResolvedValue({ data: { ...CONVERSATION, messages: [balance] } });
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "the bank says 3700" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    const card = await screen.findByRole("article", { name: "Card balance" });
    expect(within(card).getByText("Revolut: 4100.00 → 3700.00 PLN")).toBeInTheDocument();
    // Nothing is chosen for the user: Approve waits for how the difference counts.
    expect(within(card).getByLabelText("How to count the difference")).toHaveValue("");
    expect(within(card).getByRole("button", { name: "Approve" })).toBeDisabled();

    fireEvent.change(within(card).getByLabelText("How to count the difference"), {
      target: { value: "correct" },
    });
    expect(within(card).queryByLabelText("Category")).not.toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Approve" })).toBeEnabled();

    fireEvent.change(within(card).getByLabelText("How to count the difference"), {
      target: { value: "spending" },
    });

    expect(within(card).getByLabelText("Category")).toHaveValue("other");
    expect(within(card).getByLabelText("On the receipts list as")).toHaveValue(
      "Purchases not entered",
    );
  });

  it("asks with options to tap, and a tap answers with that option (F21.13.3)", async () => {
    const choice = {
      ...CARD,
      id: "q1",
      card: { kind: "choice", fields: { options: ["Main card", "Revolut"] } },
      card_state: "shown",
    };
    api.POST.mockResolvedValue({
      data: {
        ...CONVERSATION,
        messages: [
          { ...CARD, id: "a1", text: "Which card?", card: null, card_state: null },
          choice,
        ],
      },
    });
    renderPage();
    fireEvent.change(screen.getByLabelText("Write a message"), {
      target: { value: "update the balance" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    fireEvent.click(await screen.findByRole("button", { name: "Revolut" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenLastCalledWith("/api/v1/assistant/messages", {
        body: expect.objectContaining({ text: "Revolut", conversation_id: "c1" }) as unknown,
      });
    });
  });

  it("puts what was said into the field, to send or correct (F21.2.2)", async () => {
    api.POST.mockImplementation((path: string) =>
      Promise.resolve({ data: path.endsWith("/speech") ? { text: "taxi 45" } : CONVERSATION }),
    );
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Speak" }));
    fireEvent.click(await screen.findByRole("button", { name: "Stop and recognise" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Write a message")).toHaveValue("taxi 45");
    });
    expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/speech", {
      body: expect.any(FormData) as unknown,
    });
    expect(api.POST).not.toHaveBeenCalledWith("/api/v1/assistant/messages", expect.anything());
  });

  it("reads attached receipts as the Add screen does and tells the assistant (F21.8.2)", async () => {
    const reading = vi.spyOn(store.uploadStore, "readFromChat").mockResolvedValue("job1");
    renderPage();
    const photos = [new File(["a"], "a.jpg", { type: "image/jpeg" }), new File(["b"], "b.jpg")];

    const picker = document.querySelector('input[type="file"]');
    if (!(picker instanceof HTMLInputElement)) throw new Error("no file picker");
    fireEvent.change(picker, { target: { files: photos } });
    expect(screen.getByText("a.jpg")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(api.POST).toHaveBeenCalledWith("/api/v1/assistant/messages", {
        body: expect.objectContaining({
          text: "Add these receipts",
          upload_job_id: "job1",
          attached: 2,
        }) as unknown,
      });
    });
    expect(reading).toHaveBeenCalledWith(photos);
  });
});

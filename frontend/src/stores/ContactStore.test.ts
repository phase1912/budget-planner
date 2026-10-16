import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { ContactStore } from "./ContactStore";

describe("ContactStore (F17.10.2)", () => {
  it("sends the message in the screen's language, the trap field as it was", async () => {
    const api = { POST: vi.fn().mockResolvedValue({ data: { message: "ok" } }) };
    const store = new ContactStore(api as unknown as ApiClient);

    await store.send("ann@example.com", "question", "How do I add a receipt?");

    expect(api.POST).toHaveBeenCalledWith("/api/v1/contact", {
      body: {
        email: "ann@example.com",
        topic: "question",
        message: "How do I add a receipt?",
        website: "",
        language: "en",
      },
    });
    expect(store.state.status).toBe("success");
  });

  it("says why a message was refused", async () => {
    const api = {
      POST: vi.fn().mockResolvedValue({ error: { code: "rate_limited", detail: "Too many." } }),
    };
    const store = new ContactStore(api as unknown as ApiClient);

    await store.send("ann@example.com", "question", "Hello there, again");

    expect(store.state.error).toBe("Too many.");
  });
});

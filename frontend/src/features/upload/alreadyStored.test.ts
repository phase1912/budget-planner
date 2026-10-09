import { describe, expect, it } from "vitest";
import { alreadyStoredText } from "./alreadyStored";

describe("a receipt the user already has", () => {
  it("says when the stored copy was added", () => {
    const text = alreadyStoredText(
      { receipt_id: "r1", created_at: "2026-10-03T12:00:00Z" },
      "Rossmann",
    );
    expect(text).toBe(
      "Rossmann is already stored — you added it on 3 October. It will not be stored again.",
    );
  });

  it("falls back to the stored receipt's merchant when this photo has none", () => {
    const text = alreadyStoredText({
      receipt_id: "r1",
      created_at: "2026-10-03T12:00:00Z",
      merchant_name: "Żabka",
    });
    expect(text.startsWith("Żabka is already stored")).toBe(true);
  });
});

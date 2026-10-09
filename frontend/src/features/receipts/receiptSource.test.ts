import { describe, expect, it } from "vitest";

import { receiptSource } from "./receiptSource";

describe("receiptSource", () => {
  it("says how many photos a receipt was read from", () => {
    expect(receiptSource({ channel: "photo", source_reference: null, file_ids: ["a"] })).toEqual({
      label: "Added from 1 photo",
      reference: null,
    });
    expect(receiptSource({ channel: "photo", file_ids: ["a", "b"] }).label).toBe(
      "Added from 2 photos",
    );
  });

  it("names an emailed receipt and its message, without the angle brackets", () => {
    expect(
      receiptSource({
        channel: "email",
        source_reference: "<receipt-1@shop.example>",
        file_ids: [],
      }),
    ).toEqual({ label: "Added from email", reference: "receipt-1@shop.example" });
  });
});

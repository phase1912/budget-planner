import { describe, expect, it } from "vitest";

import { totalsGap } from "./receiptTotals";

describe("totalsGap", () => {
  it("forgives a grosz of rounding either way", () => {
    expect(totalsGap(188.03, 188.02)).toEqual({ kind: "match" });
    expect(totalsGap(188.01, 188.02)).toEqual({ kind: "match" });
  });

  it("reads lines above the total as a missed discount of the difference", () => {
    expect(totalsGap(226.26, 188.02)).toEqual({ kind: "over", gap: 38.24 });
  });

  it("reads lines below the total as a missing or misread line", () => {
    expect(totalsGap(10.88, 188.02)).toEqual({ kind: "under", gap: 177.14 });
  });

  it("does not let float slop in summed prices decide", () => {
    expect(totalsGap(0.1 + 0.2, 0.3)).toEqual({ kind: "match" });
  });
});

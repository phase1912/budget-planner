import { describe, expect, it } from "vitest";
import { conversionLine, converted, rateLabel } from "./exchange";

describe("a foreign receipt's conversion", () => {
  it("reads as the printed amount, the converted one and where the rate came from", () => {
    expect(
      conversionLine("1197", "UAH", "103.42", "PLN", {
        rate: "0.0864",
        rateDate: "2026-10-02",
        source: "NBP",
      }),
    ).toBe("1197.00 UAH ≈ 103.42 PLN · NBP rate, 2 October");
  });

  it("follows a total corrected in the wizard", () => {
    expect(converted("1200.00", "0.0864")).toBe("103.68");
    expect(converted(null, "0.0864")).toBeNull();
    expect(converted("", "0.0864")).toBeNull();
  });

  it("says when the owner converted it by hand", () => {
    expect(rateLabel({ rate: "0.0864", rateDate: "2026-10-03", source: "manual" })).toBe(
      "converted by you",
    );
  });
});

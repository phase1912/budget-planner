import { describe, expect, it } from "vitest";

import { paydayDue, type MonthIncome } from "./IncomeStore";

const usualOnly: MonthIncome = {
  month: "2026-10",
  total: "6800.00",
  entered: false,
  usual: "6800.00",
  entries: [],
  taxes: "0.00",
  taxes_paid: "0.00",
  regular: [],
  bills: [],
  bills_total: "0.00",
};

describe("paydayDue", () => {
  it("asks from payday on, not before", () => {
    expect(paydayDue("2026-10-09", 10, usualOnly)).toBe(false);
    expect(paydayDue("2026-10-10", 10, usualOnly)).toBe(true);
    expect(paydayDue("2026-10-25", 10, usualOnly)).toBe(true);
  });

  it("takes the 31st as the last day of a shorter month", () => {
    expect(paydayDue("2026-02-27", 31, usualOnly)).toBe(false);
    expect(paydayDue("2026-02-28", 31, usualOnly)).toBe(true);
  });

  it("does not ask once income is entered, or with nothing to offer", () => {
    expect(paydayDue("2026-10-20", 10, { ...usualOnly, entered: true })).toBe(false);
    expect(paydayDue("2026-10-20", 10, { ...usualOnly, total: null })).toBe(false);
    expect(paydayDue("2026-10-20", null, usualOnly)).toBe(false);
    expect(paydayDue("2026-10-20", 10, null)).toBe(false);
    const salary = {
      id: "s",
      name: "Salary",
      amount: "10000.00",
      day: 10,
      taxed: false,
      shared: false,
      mine: true,
      about: false,
      starts_on: "2026-10-01",
    };
    expect(paydayDue("2026-10-20", 10, { ...usualOnly, regular: [salary] })).toBe(false);
  });
});

import { afterEach, describe, expect, it } from "vitest";

import i18n from "@/i18n";
import { errorMessage, settle, UNREACHABLE } from "./errors";

const MISMATCH = {
  code: "household_currency_mismatch",
  detail: "This household keeps its budget in PLN and your account is in USD.",
  params: { household_currency: "PLN", account_currency: "USD" },
};

describe("errorMessage", () => {
  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("keeps the server's own English in English", () => {
    expect(errorMessage(MISMATCH, "fallback")).toBe(MISMATCH.detail);
  });

  it("words a refusal by its code, filled from its values, in Ukrainian", async () => {
    await i18n.changeLanguage("uk");

    expect(errorMessage(MISMATCH, "fallback")).toBe(
      "Бюджет цього домогосподарства ведеться в PLN, а ваш обліковий запис — у USD. Спільний бюджет можуть вести лише облікові записи в одній валюті.",
    );
  });

  it("writes a date it was given the way Polish does", async () => {
    await i18n.changeLanguage("pl");
    const refused = {
      code: "quota_exceeded",
      detail: "…",
      params: { limit: 30, left: 0, needed: 1, resets_on: "2026-11-01" },
    };

    expect(errorMessage(refused, "fallback")).toContain("odnowi się 1 listopada 2026");
  });

  it("falls back to the server's detail for a code it has no words for", async () => {
    await i18n.changeLanguage("uk");

    expect(errorMessage({ code: "something_new", detail: "Server says so." }, "fallback")).toBe(
      "Server says so.",
    );
  });

  it("says the server could not be reached in the user's language", async () => {
    await i18n.changeLanguage("pl");

    expect(errorMessage(UNREACHABLE, "fallback")).toBe(
      "Nie udało się połączyć z serwerem. Spróbuj za chwilę.",
    );
  });
});

describe("settle", () => {
  it("wraps a rejected promise in UNREACHABLE error", async () => {
    const res = await settle(() => Promise.reject(new Error("network failed")));
    expect(res).toEqual({ error: UNREACHABLE });
  });

  it("wraps an undefined resolution in UNREACHABLE error", async () => {
    const res = await settle(() => Promise.resolve(undefined as unknown as { error?: unknown }));
    expect(res).toEqual({ error: UNREACHABLE });
  });
});

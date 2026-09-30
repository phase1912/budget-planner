import { describe, expect, it } from "vitest";

import { timeAgo } from "./timeAgo";

const NOW = new Date("2026-09-30T12:00:00Z").getTime();

describe("timeAgo", () => {
  it.each([
    ["2026-09-30T11:59:30Z", "just now"],
    ["2026-09-30T11:55:00Z", "5 minutes ago"],
    ["2026-09-30T09:00:00Z", "3 hours ago"],
    ["2026-09-29T10:00:00Z", "yesterday"],
    ["2026-09-20T12:00:00Z", "10 days ago"],
  ])("reads %s as %s", (iso, words) => {
    expect(timeAgo(iso, NOW)).toBe(words);
  });
});

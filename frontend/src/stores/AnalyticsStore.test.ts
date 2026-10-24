import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { AnalyticsStore, reportDays } from "./AnalyticsStore";

function storeWithApi() {
  const api = { POST: vi.fn().mockResolvedValue({ data: undefined }) };
  return { api, store: new AnalyticsStore(api as unknown as ApiClient) };
}

const bodies = (api: { POST: ReturnType<typeof vi.fn> }) =>
  api.POST.mock.calls.map((call: unknown[]) => call[1]);

describe("AnalyticsStore (F17.3)", () => {
  it("sends the first public page of a load as the visit, with its source; later pages not", () => {
    const { api, store } = storeWithApi();

    store.countView("/", "https://l.instagram.com/", "?utm_source=insta", false, 0);
    store.countView("/receipts", "https://l.instagram.com/", "", false, 2000);
    store.countView("/register", "https://l.instagram.com/", "", false, 4000);

    expect(bodies(api)).toEqual([
      {
        body: {
          page: "/",
          referrer: "https://l.instagram.com/",
          utm_source: "insta",
          entry: true,
          platform: "web",
        },
      },
      {
        body: {
          page: "/register",
          referrer: null,
          utm_source: null,
          entry: false,
          platform: "web",
        },
      },
    ]);
  });

  it("counts nothing for a signed-in reader: their use is their activity, not a visit", () => {
    const { api, store } = storeWithApi();

    store.countView("/help", "", "", true, 0);

    expect(api.POST).not.toHaveBeenCalled();
  });

  it("counts one opening once, even when the effect runs twice", () => {
    const { api, store } = storeWithApi();

    store.countView("/help", "", "", false, 1000);
    store.countView("/help", "", "", false, 1100);
    store.countView("/help", "", "", false, 5000);

    expect(api.POST).toHaveBeenCalledTimes(2);
  });

  it("reports the last 7 or 30 days, both ends counted, ending today", () => {
    const today = new Date(2026, 9, 17);

    expect(reportDays("last_7", today)).toEqual(["2026-10-11", "2026-10-17"]);
    expect(reportDays("last_30", today)).toEqual(["2026-09-18", "2026-10-17"]);
    expect(reportDays("this_month", today)).toEqual(["2026-10-01", "2026-10-17"]);
  });
});

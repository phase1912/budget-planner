import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient, patientFetch } from "@/api/client";
import { onSlowReads } from "@/api/coldStart";

describe("apiClient", () => {
  it("sends typed requests to the configured base URL", async () => {
    const fetchMock = vi.fn((request: Request) => {
      expect(request.url).toBe("http://localhost:8000/health");
      return Promise.resolve(
        new Response(JSON.stringify({ status: "ok", database: { reachable: true } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    const { data, error } = await apiClient.GET("/health", { fetch: fetchMock });

    expect(error).toBeUndefined();
    expect(data).toEqual({ status: "ok", database: { reachable: true } });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});

describe("patientFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("tries a read that failed once more, as a cold start may have dropped it", async () => {
    const fetch = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Load failed"))
      .mockResolvedValueOnce(new Response("{}"));
    vi.stubGlobal("fetch", fetch);

    const response = await patientFetch(new Request("https://api.test/receipts"));

    expect(response.ok).toBe(true);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("never repeats a write, which may have landed before it failed", async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError("Load failed"));
    vi.stubGlobal("fetch", fetch);

    await expect(
      patientFetch(new Request("https://api.test/receipts", { method: "POST", body: "{}" })),
    ).rejects.toThrow("Load failed");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("gives every request a deadline instead of letting it hang", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);

    await patientFetch(new Request("https://api.test/receipts"));

    const init = fetch.mock.calls[0]?.[1] as RequestInit;
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it("reports a read still waiting after a few seconds as the server starting", async () => {
    vi.useFakeTimers();
    let answer: (response: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => (answer = resolve))),
    );
    const reports: boolean[] = [];
    const stop = onSlowReads((waiting) => reports.push(waiting));

    const pending = patientFetch(new Request("https://api.test/receipts"));
    await vi.advanceTimersByTimeAsync(5_000);
    answer(new Response("{}"));
    await pending;
    stop();
    vi.useRealTimers();

    expect(reports).toEqual([true, false]);
  });
});

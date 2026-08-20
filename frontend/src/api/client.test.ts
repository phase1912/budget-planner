import { describe, expect, it, vi } from "vitest";

import { apiClient } from "@/api/client";

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

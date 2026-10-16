import { describe, expect, it } from "vitest";

import { ServerStore } from "./ServerStore";

describe("ServerStore", () => {
  it("says the server is starting while reads wait long, and stops once they answer", () => {
    let report: (waiting: boolean) => void = () => undefined;
    const store = new ServerStore((listener) => {
      report = listener;
      return () => undefined;
    });

    report(true);
    expect(store.isWaking).toBe(true);
    report(false);
    expect(store.isWaking).toBe(false);
  });
});

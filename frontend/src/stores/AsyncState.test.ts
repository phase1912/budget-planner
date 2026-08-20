import { describe, expect, it } from "vitest";

import { AsyncState } from "@/stores/AsyncState";

describe("AsyncState", () => {
  it("starts idle with no error", () => {
    const state = new AsyncState();

    expect(state.status).toBe("idle");
    expect(state.error).toBeNull();
    expect(state.isLoading).toBe(false);
  });

  it("start moves to loading and clears any previous error", () => {
    const state = new AsyncState();
    state.fail("boom");

    state.start();

    expect(state.status).toBe("loading");
    expect(state.error).toBeNull();
    expect(state.isLoading).toBe(true);
  });

  it("succeed moves to success and clears any error", () => {
    const state = new AsyncState();
    state.start();

    state.succeed();

    expect(state.status).toBe("success");
    expect(state.error).toBeNull();
  });

  it("fail moves to error and records the message", () => {
    const state = new AsyncState();
    state.start();

    state.fail("network unreachable");

    expect(state.status).toBe("error");
    expect(state.error).toBe("network unreachable");
    expect(state.isLoading).toBe(false);
  });

  it("reset returns to idle with no error", () => {
    const state = new AsyncState();
    state.fail("boom");

    state.reset();

    expect(state.status).toBe("idle");
    expect(state.error).toBeNull();
  });
});

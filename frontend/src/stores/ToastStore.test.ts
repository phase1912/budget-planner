import { describe, it, expect, beforeEach, vi } from "vitest";

const feel = vi.hoisted(() => vi.fn(() => Promise.resolve()));
vi.mock("@/platform", () => ({ device: { feel } }));

import { ToastStore } from "./ToastStore";

describe("ToastStore", () => {
  let store: ToastStore;

  beforeEach(() => {
    store = new ToastStore();
  });

  it("should initialize with no toast", () => {
    expect(store.toast).toBeNull();
  });

  it("should set an error toast", () => {
    store.showError("Network error");
    expect(store.toast).toEqual({ message: "Network error", type: "error" });
  });

  it("should set a success toast", () => {
    store.showSuccess("Saved successfully");
    expect(store.toast).toEqual({ message: "Saved successfully", type: "success" });
  });

  it("should set an info toast", () => {
    store.showInfo("Update available");
    expect(store.toast).toEqual({ message: "Update available", type: "info" });
  });

  it("should clear the toast", () => {
    store.showError("Network error");
    store.clearToast();
    expect(store.toast).toBeNull();
  });

  it("buzzes the phone for a success and for a failure, never for a plain note", () => {
    feel.mockClear();
    store.showSuccess("Saved");
    store.showError("Failed");
    store.showInfo("Note");

    expect(feel.mock.calls).toEqual([["saved"], ["failed"]]);
  });
});

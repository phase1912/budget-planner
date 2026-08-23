import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ToastContainer } from "./Toast";
import type { ToastStore } from "@/stores/ToastStore";

// Mock the store context
let mockToastStore: Partial<ToastStore>;

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    toastStore: mockToastStore,
  }),
}));

describe("ToastContainer", () => {
  beforeEach(() => {
    mockToastStore = {
      toast: null,
      clearToast: vi.fn(),
    };
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("renders nothing when there is no toast", () => {
    const { container } = render(<ToastContainer />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders an error toast and auto-closes after 5 seconds", () => {
    mockToastStore.toast = { message: "Test error message", type: "error" };
    render(<ToastContainer />);

    expect(screen.getByText("Test error message")).toBeInTheDocument();

    // Fast-forward 5 seconds
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(mockToastStore.clearToast).toHaveBeenCalledTimes(1);
  });

  it("allows closing the toast manually", () => {
    mockToastStore.toast = { message: "Test success message", type: "success" };
    render(<ToastContainer />);

    const closeBtn = screen.getByRole("button", { name: /close/i });
    fireEvent.click(closeBtn);

    expect(mockToastStore.clearToast).toHaveBeenCalledTimes(1);
  });
});

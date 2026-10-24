import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
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

  it("renders an info toast correctly", () => {
    mockToastStore.toast = { message: "Test info message", type: "info" };
    render(<ToastContainer />);

    expect(screen.getByText("Test info message")).toBeInTheDocument();
  });

  it("allows closing the toast manually", () => {
    mockToastStore.toast = { message: "Test success message", type: "success" };
    render(<ToastContainer />);

    const closeBtn = screen.getByRole("button", { name: /close/i });
    fireEvent.click(closeBtn);

    expect(mockToastStore.clearToast).toHaveBeenCalledTimes(1);
  });

  it.each(["success", "error", "info"] as const)(
    "a %s toast sits on an opaque background, so the header never shows through it",
    (type) => {
      mockToastStore.toast = { message: "3 receipts stored", type };
      render(<ToastContainer />);

      const toast = screen.getByRole(type === "error" ? "alert" : "status");
      expect(toast.parentElement).toHaveClass("bg-background");
    },
  );

  it("colours a success toast with the primary tone, the design system's success", () => {
    mockToastStore.toast = { message: "1 receipt stored", type: "success" };
    render(<ToastContainer />);

    expect(screen.getByRole("status")).toHaveClass("bg-tone-primary-bg", "text-tone-primary-text");
  });

  it("offers where to go next when the message has a link (F24.3)", () => {
    mockToastStore.toast = {
      message: "Saved. 1 receipt is dated February 2019: it is in that month, not this one.",
      type: "success",
      link: { to: "/receipts?start=2019-02-01&end=2019-02-28", label: "Open February 2019" },
    };
    render(
      <MemoryRouter>
        <ToastContainer />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Open February 2019" })).toHaveAttribute(
      "href",
      "/receipts?start=2019-02-01&end=2019-02-28",
    );
  });
});

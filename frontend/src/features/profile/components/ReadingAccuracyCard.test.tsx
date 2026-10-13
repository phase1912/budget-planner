import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ReadingAccuracy } from "@/stores/AccuracyStore";
import { ReadingAccuracyCard } from "./ReadingAccuracyCard";

const accuracy = vi.hoisted(() => ({
  report: null as ReadingAccuracy | null,
  load: vi.fn(),
}));

vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({ accuracyStore: accuracy }),
}));

const EMPTY: ReadingAccuracy = {
  receipts: 0,
  corrected_receipts: 0,
  lines: 0,
  corrected_lines: 0,
  remembered_lines: 0,
  shops: [],
  months: [],
};

describe("ReadingAccuracyCard (F15.4)", () => {
  it("says how many receipts needed a correction, from which shops, month by month", () => {
    accuracy.report = {
      receipts: 20,
      corrected_receipts: 4,
      lines: 120,
      corrected_lines: 6,
      remembered_lines: 3,
      shops: [{ merchant: "Biedronka", receipts: 9, corrected: 4 }],
      months: [
        { month: "2026-09-01", receipts: 12, corrected: 3 },
        { month: "2026-10-01", receipts: 0, corrected: 0 },
      ],
    } satisfies ReadingAccuracy;
    render(<ReadingAccuracyCard />);

    expect(
      screen.getByText("4 of 20 receipts read in the last 6 months needed a correction (20%)."),
    ).toBeInTheDocument();
    expect(screen.getByText(/You changed 6 of 120 lines\./)).toBeInTheDocument();
    expect(screen.getByText(/fixed 3 more lines by themselves/)).toBeInTheDocument();
    expect(screen.getByText("Biedronka")).toBeInTheDocument();
    expect(screen.getByText("4 of 9 receipts")).toBeInTheDocument();
    const trend = screen.getByRole("list", { name: "Month by month" });
    expect(within(trend).getByText("3 of 12 receipts")).toBeInTheDocument();
    expect(within(trend).getByText("no receipts")).toBeInTheDocument();
    expect(accuracy.load).toHaveBeenCalled();
  });

  it("says there is nothing to measure before any receipt is read", () => {
    accuracy.report = EMPTY;
    render(<ReadingAccuracyCard />);

    expect(screen.getByText(/nothing to measure yet/)).toBeInTheDocument();
  });
});

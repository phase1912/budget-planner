import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Info } from "lucide-react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders title and message", () => {
    render(<EmptyState icon={Info} title="No items" message="Check back later." />);
    expect(screen.getByText("No items")).toBeInTheDocument();
    expect(screen.getByText("Check back later.")).toBeInTheDocument();
  });

  it("renders action if provided", () => {
    render(
      <EmptyState
        icon={Info}
        title="No items"
        message="Check back later."
        action={<button>Refresh</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });
});

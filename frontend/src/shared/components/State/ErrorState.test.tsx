import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("renders title and message in panel layout by default", () => {
    render(<ErrorState title="Something went wrong" message="Please try again." />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Please try again.")).toBeInTheDocument();
  });

  it("renders action if provided", () => {
    render(
      <ErrorState 
        title="Error" 
        message="Failed" 
        action={<button>Retry</button>}
      />
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders in banner layout", () => {
    const { container } = render(
      <ErrorState title="Banner Error" message="Banner Message" layout="banner" />
    );
    expect(screen.getByText("Banner Error")).toBeInTheDocument();
    // Verify it uses the banner layout classes
    expect(container.firstChild).toHaveClass("bg-tone-error-bg");
  });
});

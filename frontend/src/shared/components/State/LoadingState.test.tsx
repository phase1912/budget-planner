import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { LoadingState } from "./LoadingState";

describe("LoadingState", () => {
  it("renders default title", () => {
    render(<LoadingState />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders custom title and message", () => {
    render(<LoadingState title="Fetching" message="Please wait" />);
    expect(screen.getByText("Fetching")).toBeInTheDocument();
    expect(screen.getByText("Please wait")).toBeInTheDocument();
  });

  it("renders spinner layout", () => {
    const { container } = render(<LoadingState layout="spinner" />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });
});

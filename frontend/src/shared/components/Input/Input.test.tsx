import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Input } from "./Input";

describe("Input", () => {
  it("renders with correct accessibility role and label", () => {
    render(<Input label="Username" id="username" />);
    const input = screen.getByLabelText("Username");
    expect(input).toBeInTheDocument();
    expect(input).toHaveRole("textbox");
  });

  it("displays error message when provided", () => {
    render(<Input error="Invalid input" />);
    expect(screen.getByText("Invalid input")).toBeInTheDocument();
  });

  it("is disabled when disabled prop is true", () => {
    render(<Input disabled label="Username" id="username" />);
    expect(screen.getByLabelText("Username")).toBeDisabled();
  });

  it("ties its label to the field even when no id is given", () => {
    render(<Input label="Merchant" />);
    expect(screen.getByLabelText("Merchant")).toHaveRole("textbox");
  });

  it("puts layout classes on the wrapper a grid lays out, not on the field", () => {
    render(<Input aria-label="Name" containerClassName="col-span-3" className="text-right" />);
    const field = screen.getByLabelText("Name");
    expect(field.parentElement).toHaveClass("col-span-3");
    expect(field).toHaveClass("text-right");
    expect(field).not.toHaveClass("col-span-3");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Select } from "./Select";

describe("Select", () => {
  it("renders with correct accessibility role", () => {
    render(
      <Select label="Options" id="options">
        <option>One</option>
      </Select>,
    );
    const select = screen.getByLabelText("Options");
    expect(select).toBeInTheDocument();
    expect(select).toHaveRole("combobox");
  });

  it("displays error message when provided", () => {
    render(<Select error="Select an option" />);
    expect(screen.getByText("Select an option")).toBeInTheDocument();
  });

  it("is disabled when disabled prop is true", () => {
    render(
      <Select disabled label="Options" id="options">
        <option>One</option>
      </Select>,
    );
    expect(screen.getByLabelText("Options")).toBeDisabled();
  });
});

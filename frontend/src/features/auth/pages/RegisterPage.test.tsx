import { fireEvent, render, screen, within } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { RegisterPage } from "./RegisterPage";

// Mock the store context
vi.mock("@/stores/StoreContext", () => ({
  useStores: () => ({
    authStore: {
      authState: { isLoading: false, error: null },
      register: vi.fn().mockResolvedValue(true),
    },
  }),
}));

describe("RegisterPage", () => {
  it("renders the registration form", () => {
    render(
      <BrowserRouter>
        <RegisterPage />
      </BrowserRouter>,
    );
    expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /register/i })).toBeInTheDocument();
  });

  function renderPage() {
    render(
      <BrowserRouter>
        <RegisterPage />
      </BrowserRouter>,
    );
    const type = (label: RegExp, value: string) => {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    };
    return { type };
  }

  it("ticks off each password rule as it is met, and holds Register until all are", () => {
    const { type } = renderPage();
    const checklist = within(screen.getByRole("list", { name: "What the password needs" }));

    type(/^password/i, "kawa");
    expect(checklist.getByText("At least 8 characters")).toHaveTextContent("missing");
    expect(checklist.getByText("A letter")).toHaveTextContent("done");
    expect(checklist.getByText("A digit")).toHaveTextContent("missing");
    expect(screen.getByRole("button", { name: /register/i })).toBeDisabled();

    type(/^password/i, "Kawa-2026");
    type(/confirm password/i, "Kawa-2026");
    expect(checklist.getByText(/special character/)).toHaveTextContent("done");
    expect(checklist.getByText("Both passwords match")).toHaveTextContent("done");
    expect(screen.getByRole("button", { name: /register/i })).toBeEnabled();
  });

  it("says when the two passwords differ", () => {
    const { type } = renderPage();
    type(/^password/i, "Kawa-2026");
    type(/confirm password/i, "Kawa-2027");
    expect(screen.getByText("Both passwords match")).toHaveTextContent("missing");
    expect(screen.getByRole("button", { name: /register/i })).toBeDisabled();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, it, expect, vi } from "vitest";
import { LoginPage } from "./LoginPage";

const stores = vi.hoisted(() => ({
  serverStore: { wake: vi.fn() },
  signInStore: { available: [], loadProviders: vi.fn() },
  authStore: {
    authState: { isLoading: false, error: null },
    secondFactorToken: null as string | null,
    login: vi.fn().mockResolvedValue(true),
    completeSecondFactor: vi.fn().mockResolvedValue(true),
    cancelSecondFactor: vi.fn(),
  },
}));

vi.mock("@/stores/StoreContext", () => ({ useStores: () => stores }));

const renderPage = () =>
  render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>,
  );

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stores.authStore.secondFactorToken = null;
  });

  it("renders the login form", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /welcome back/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("asks for the authenticator code after the password of a two-factor account (F18.6.1)", () => {
    stores.authStore.secondFactorToken = "challenge";
    renderPage();

    expect(screen.getByRole("heading", { name: "Enter your code" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(stores.authStore.completeSecondFactor).toHaveBeenCalledWith("123456");

    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(stores.authStore.cancelSecondFactor).toHaveBeenCalled();
  });
});

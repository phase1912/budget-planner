import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RootStore } from "@/stores/RootStore";
import { StoreProvider } from "@/stores/StoreContext";
import { AiConsentDialog } from "./AiConsentDialog";

describe("AiConsentDialog (F25.3.2)", () => {
  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
    rootStore.authStore.user = {
      id: "u1",
      first_name: "Ann",
      ai_consent_at: null,
    } as unknown as typeof rootStore.authStore.user;
  });

  const renderDialog = () =>
    render(
      <StoreProvider store={rootStore}>
        <AiConsentDialog />
      </StoreProvider>,
    );

  it("says what goes to the AI, to whom and why, and allows it only when asked", () => {
    const allow = vi.spyOn(rootStore.profileStore, "setAiConsent").mockResolvedValue(true);
    renderDialog();

    expect(screen.getByRole("dialog", { name: "Let the AI read your receipts?" })).toBeVisible();
    expect(screen.getByText(/Google's Gemini models on Vertex AI/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Allow" }));

    expect(allow).toHaveBeenCalledWith(true);
  });

  it("goes away on 'not now' without allowing anything", () => {
    const allow = vi.spyOn(rootStore.profileStore, "setAiConsent");
    renderDialog();

    fireEvent.click(screen.getByRole("button", { name: "Not now" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(allow).not.toHaveBeenCalled();
  });

  it("is not asked again once allowed", () => {
    if (rootStore.authStore.user) rootStore.authStore.user.ai_consent_at = "2026-10-24T10:00:00Z";
    renderDialog();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

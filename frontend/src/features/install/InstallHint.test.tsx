import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InstallHint } from "./InstallHint";

const installStore = {
  dismissed: false,
  offersInstall: false,
  showsIosHint: false,
  install: vi.fn(),
  dismiss: vi.fn(),
};

vi.mock("@/stores/StoreContext", () => ({ useStores: () => ({ installStore }) }));

function given(state: Partial<typeof installStore>) {
  Object.assign(
    installStore,
    { dismissed: false, offersInstall: false, showsIosHint: false },
    state,
  );
  render(<InstallHint />);
}

describe("InstallHint", () => {
  it("tells an iPhone where the Add to Home Screen step is", () => {
    given({ showsIosHint: true });
    expect(screen.getByText("Add to Home Screen")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Install app/ })).toBeNull();
  });

  it("opens the browser's install dialog where there is one", () => {
    given({ offersInstall: true });
    fireEvent.click(screen.getByRole("button", { name: /Install app/ }));
    expect(installStore.install).toHaveBeenCalled();
  });

  it("can be dismissed", () => {
    given({ showsIosHint: true });
    fireEvent.click(screen.getByRole("button", { name: "Dismiss the install hint" }));
    expect(installStore.dismiss).toHaveBeenCalled();
  });

  it("shows nothing when installing is not possible or already done", () => {
    given({});
    expect(screen.queryByText(/home screen/i)).toBeNull();
  });
});

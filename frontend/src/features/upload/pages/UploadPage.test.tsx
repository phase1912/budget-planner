import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { UploadPage } from "./UploadPage";
import { StoreProvider } from "@/stores/StoreContext";
import { UploadStore } from "@/stores/UploadStore";
import type { ApiClient } from "@/api/client";
import type { RootStore } from "@/stores/RootStore";

describe("UploadPage", () => {
  it("renders the upload button in idle state", () => {
    const mockApi = { POST: vi.fn() };
    const uploadStore = new UploadStore(mockApi as unknown as ApiClient);

    const mockStores = { uploadStore } as unknown as RootStore;

    render(
      <StoreProvider store={mockStores}>
        <UploadPage />
      </StoreProvider>,
    );

    expect(screen.getByText("Add a receipt")).toBeInTheDocument();
  });

  it("renders the error panel when there is an error", () => {
    const mockApi = { POST: vi.fn() };
    const uploadStore = new UploadStore(mockApi as unknown as ApiClient);
    uploadStore.uploadState.fail("Test Error");
    uploadStore.errorTitle = "Unsupported file";
    uploadStore.errorDetails = "This file type is not supported.";

    const mockStores = { uploadStore } as unknown as RootStore;

    render(
      <StoreProvider store={mockStores}>
        <UploadPage />
      </StoreProvider>,
    );

    expect(screen.getByText("Unsupported file")).toBeInTheDocument();
    expect(screen.getByText("This file type is not supported.")).toBeInTheDocument();
  });
});

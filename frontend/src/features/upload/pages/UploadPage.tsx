import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import React, { useRef } from "react";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Card } from "@/shared/components/Card/Card";
import { Button } from "@/shared/components/Button/Button";

export const UploadPage = observer(function UploadPage() {
  const { uploadStore } = useStores();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length > 0) {
      uploadStore.addFiles(files);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleUploadClick = () => {
    if (!uploadStore.isOverLimit && uploadStore.files.length > 0) {
      void uploadStore.submitUpload();
    }
  };

  const isOverSize = uploadStore.totalSize > 50 * 1024 * 1024;
  const isOverCount = uploadStore.files.length > 10;

  // Calculate percentage of 50MB (max 100%)
  const sizePercentage = Math.min(100, (uploadStore.totalSize / (50 * 1024 * 1024)) * 100);
  // Calculate percentage of 10 photos (max 100%)
  const countPercentage = Math.min(100, (uploadStore.files.length / 10) * 100);
  const fillPercentage = Math.max(sizePercentage, countPercentage);

  return (
    <Container size="narrow" className="py-9">
      <Stack className="gap-6">
        <div className="flex items-center">
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-7 h-7 border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              1
            </span>
            <span className="text-sm font-semibold text-foreground">Photos</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-border mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-7 h-7 border border-border rounded-pill bg-background text-border-strong text-[13px] font-bold">
              2
            </span>
            <span className="text-sm font-semibold text-border-strong">What we read</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-border mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-7 h-7 border border-border rounded-pill bg-background text-border-strong text-[13px] font-bold">
              3
            </span>
            <span className="text-sm font-semibold text-border-strong">Resolve</span>
          </span>
        </div>

        <div>
          <h1 className="m-0 text-[30px] font-bold tracking-tight">Add the photos</h1>
          <p className="m-0 text-[15px] text-muted-foreground mt-1">
            JPEG, PNG, HEIC or a PDF scan. Up to 10 photos and 50&nbsp;MB per receipt.
          </p>
        </div>

        <div
          className="inline-flex gap-1 border border-border rounded-control bg-muted p-1 self-start"
          role="tablist"
        >
          <button
            className={`inline-flex items-center gap-2 border-none rounded-[9px] px-4 py-[9px] text-sm cursor-pointer transition-colors ${
              uploadStore.mode === "single"
                ? "bg-background text-foreground shadow-raised"
                : "bg-transparent text-muted-foreground hover:text-foreground"
            }`}
            role="tab"
            aria-selected={uploadStore.mode === "single"}
            onClick={() => {
              uploadStore.setMode("single");
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
              <path d="M16 8H8" />
              <path d="M16 12H8" />
            </svg>
            One receipt
          </button>
          <button
            className={`inline-flex items-center gap-2 border-none rounded-[9px] px-4 py-[9px] text-sm cursor-pointer transition-colors ${
              uploadStore.mode === "multiple"
                ? "bg-background text-foreground shadow-raised"
                : "bg-transparent text-muted-foreground hover:text-foreground"
            }`}
            role="tab"
            aria-selected={uploadStore.mode === "multiple"}
            onClick={() => {
              uploadStore.setMode("multiple");
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 17 22 12" />
            </svg>
            Several receipts
          </button>
        </div>

        <Stack className="gap-4">
          {uploadStore.mode === "single" && uploadStore.files.length > 0 && (
            <Card
              variant="surface"
              className={`p-5 ${uploadStore.isOverLimit ? "border-tone-error-border" : ""}`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`inline-flex items-center justify-center w-[26px] h-[26px] rounded-pill text-xs font-bold ${uploadStore.isOverLimit ? "bg-tone-error-bg text-tone-error-text" : "bg-tone-primary-bg text-tone-primary-text"}`}
                  >
                    1
                  </span>
                  <span className="text-[15px] font-semibold">Receipt</span>
                </div>
              </div>

              <div className="flex items-center gap-2.5 mb-4 flex-wrap">
                {uploadStore.files.map((_, i) => (
                  <span
                    key={i}
                    className="relative inline-flex items-center justify-center border border-border rounded-chip bg-muted w-[72px] h-[88px] overflow-hidden"
                  >
                    <span className="absolute bottom-1 right-1 text-[10px] text-muted-foreground">
                      {i + 1}
                    </span>
                    <button
                      onClick={() => {
                        uploadStore.removeFile(i);
                      }}
                      className="absolute top-1 left-1 bg-background border border-border rounded-full w-[18px] h-[18px] flex items-center justify-center cursor-pointer z-10 hover:bg-muted text-foreground"
                      aria-label="Remove photo"
                    >
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                      </svg>
                    </button>
                  </span>
                ))}

                <button
                  className="inline-flex flex-col items-center justify-center gap-1.5 border border-dashed border-border-strong rounded-chip bg-background text-primary font-medium w-[72px] h-[88px] cursor-pointer hover:bg-muted"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M5 12h14" />
                    <path d="M12 5v14" />
                  </svg>
                  <span className="text-xs">Add</span>
                </button>
              </div>

              {uploadStore.isOverLimit && (
                <div className="flex items-start gap-2.5 rounded-card p-3 mb-4 bg-tone-error-bg text-tone-error-text">
                  <svg
                    className="mt-[2px] text-tone-error-text shrink-0"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v4" />
                    <path d="M12 16h.01" />
                  </svg>
                  <span className="text-[13px] font-medium text-tone-error-text">
                    {isOverCount
                      ? `${String(uploadStore.files.length - 10)} photos were not added — a receipt takes at most 10.`
                      : `The photos add up to ${uploadStore.totalSizeMB} MB, exceeding the 50 MB limit.`}
                  </span>
                </div>
              )}

              <Stack className="gap-[5px]">
                <div className="flex items-baseline justify-between">
                  <span
                    className={`text-xs ${isOverCount ? "font-semibold text-error" : "text-muted-foreground"}`}
                  >
                    {uploadStore.files.length} of 10 photos
                  </span>
                  <span
                    className={`text-xs ${isOverSize ? "font-semibold text-error" : "text-muted-foreground"}`}
                  >
                    {uploadStore.totalSizeMB} of 50&nbsp;MB
                  </span>
                </div>
                <span className="block h-[4px] rounded-[2px] bg-border overflow-hidden">
                  <span
                    className={`block h-full rounded-[2px] ${uploadStore.isOverLimit ? "bg-error" : "bg-primary"}`}
                    style={{ width: `${String(fillPercentage)}%` }}
                  ></span>
                </span>
              </Stack>
            </Card>
          )}

          {uploadStore.mode === "single" && uploadStore.files.length === 0 && (
            <Card variant="surface" className="p-5">
              <button
                className="inline-flex flex-row items-center justify-center gap-2 border border-dashed border-border-strong rounded-card bg-background text-primary font-medium text-sm p-4 w-full cursor-pointer hover:bg-muted"
                onClick={() => fileInputRef.current?.click()}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 12h14" />
                  <path d="M12 5v14" />
                </svg>
                Add a receipt
              </button>
            </Card>
          )}

          {uploadStore.mode === "multiple" && (
            <Card variant="surface" className="p-5">
              <p className="text-sm text-muted-foreground m-0">
                Multiple receipts mode not yet implemented.
              </p>
            </Card>
          )}

          {uploadStore.uploadState.status === "success" && (
            <div className="card card--flush panel mt-4">
              <div className="panel__body">
                <div className="note note--success w-full">
                  <div className="flex flex-col gap-1">
                    <span className="text-[13px] font-bold text-success">
                      Files successfully added!
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {uploadStore.uploadState.status === "error" && uploadStore.errorTitle && (
            <div className="card card--flush panel mt-4 card--attention">
              <div className="panel__label">
                <span className="panel__title">{uploadStore.errorTitle}</span>
                <span className="panel__ref">ERR</span>
              </div>
              <div className="panel__body">
                <div className="note note--error items-start w-full">
                  <svg
                    className="note__icon mt-0.5"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v4" />
                    <path d="M12 16h.01" />
                  </svg>
                  <div className="flex flex-col gap-1">
                    <span className="text-[13px] font-bold">Upload failed</span>
                    <span className="text-xs leading-relaxed">{uploadStore.errorDetails}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            multiple
            onChange={handleFileChange}
            accept="image/jpeg, image/png, image/heic, application/pdf"
          />
        </Stack>

        {uploadStore.files.length > 0 && uploadStore.mode === "single" && (
          <div className="flex items-center justify-between gap-4 border-t border-border pt-5">
            <span className="text-[13px] text-muted-foreground">
              1 receipt &middot; {uploadStore.files.length} photos &middot;{" "}
              {uploadStore.totalSizeMB}&nbsp;MB total
            </span>
            <div className="flex items-center gap-3">
              <Button variant="ghost">Cancel</Button>
              <Button
                variant="primary"
                onClick={handleUploadClick}
                disabled={uploadStore.isOverLimit || uploadStore.uploadState.status === "loading"}
              >
                {uploadStore.uploadState.status === "loading" ? "Sending..." : "Read these photos"}
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </Button>
            </div>
          </div>
        )}
      </Stack>
    </Container>
  );
});

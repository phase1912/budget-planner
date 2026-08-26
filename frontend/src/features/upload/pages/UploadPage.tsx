import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import React, { useRef } from "react";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Card } from "@/shared/components/Card/Card";
import { Button } from "@/shared/components/Button/Button";
import { SecureImage } from "@/shared/components";
import { ReceiptLineCard } from "../components/ReceiptLineCard";

export const UploadPage = observer(function UploadPage() {
  const { uploadStore } = useStores();
  const singleInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = () => {
    if (!uploadStore.isAnyLineOverLimit && uploadStore.totalFilesCount > 0) {
      void uploadStore.submitUpload();
    }
  };

  const handleSingleInitialUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length > 0) {
      uploadStore.addFilesToLine(0, files);
      if (singleInputRef.current) {
        singleInputRef.current.value = "";
      }
    }
  };

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
          {uploadStore.lines.map((lineFiles, index) => {
            // In single mode, if there are no files, we show the initial upload button below
            if (uploadStore.mode === "single" && lineFiles.length === 0) return null;

            return (
              <ReceiptLineCard
                key={index}
                index={index}
                files={lineFiles}
                totalSizeMB={uploadStore.getLineTotalSizeMB(index)}
                isOverLimit={uploadStore.isLineOverLimit(index)}
                isOverCount={lineFiles.length > 10}
                isOverSize={uploadStore.getLineTotalSize(index) > 50 * 1024 * 1024}
                onAddFiles={(files) => {
                  uploadStore.addFilesToLine(index, files);
                }}
                onRemoveFile={(fileIndex) => {
                  uploadStore.removeFileFromLine(index, fileIndex);
                }}
                onRemoveLine={() => {
                  uploadStore.removeLine(index);
                }}
                showRemoveLine={uploadStore.mode === "multiple" && uploadStore.lines.length > 1}
              />
            );
          })}

          {uploadStore.mode === "single" && uploadStore.files.length === 0 && (
            <Card variant="surface" className="p-5">
              <button
                className="inline-flex flex-row items-center justify-center gap-2 border border-dashed border-border-strong rounded-card bg-background text-primary font-medium text-sm p-4 w-full cursor-pointer hover:bg-muted"
                onClick={() => singleInputRef.current?.click()}
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
              <input
                type="file"
                ref={singleInputRef}
                className="hidden"
                multiple
                onChange={handleSingleInitialUpload}
                accept="image/jpeg, image/png, image/heic, application/pdf"
              />
            </Card>
          )}

          {uploadStore.mode === "multiple" && (
            <button
              className="inline-flex flex-row items-center justify-center gap-2 border border-dashed border-border-strong rounded-card bg-background text-primary font-medium text-sm p-4 w-full cursor-pointer hover:bg-muted"
              onClick={() => {
                uploadStore.addLine();
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
                <path d="M5 12h14" />
                <path d="M12 5v14" />
              </svg>
              Add another receipt
            </button>
          )}

          {uploadStore.uploadState.status === "success" && (
            <div className="card card--flush panel mt-4">
              <div className="panel__body">
                <div className="note note--success w-full mb-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[13px] font-bold text-success">
                      Files successfully added!
                    </span>
                  </div>
                </div>
                {uploadStore.fileIds.length > 0 && (
                  <div className="flex flex-wrap gap-2 px-4 pb-4">
                    {uploadStore.fileIds.map((id) => (
                      <SecureImage
                        key={id}
                        fileId={id}
                        alt="Uploaded receipt"
                        className="w-[72px] h-[88px] object-cover rounded-chip border border-border"
                      />
                    ))}
                  </div>
                )}
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
        </Stack>

        {uploadStore.totalFilesCount > 0 && (
          <div className="flex items-center justify-between gap-4 border-t border-border pt-5">
            <span className="text-[13px] text-muted-foreground">
              {uploadStore.lines.length} receipt{uploadStore.lines.length === 1 ? "" : "s"} &middot;{" "}
              {uploadStore.totalFilesCount} photos &middot; {uploadStore.allLinesTotalSizeMB}
              &nbsp;MB total
            </span>
            <div className="flex items-center gap-3">
              <Button variant="ghost">Cancel</Button>
              <Button
                variant="primary"
                onClick={handleUploadClick}
                disabled={
                  uploadStore.isAnyLineOverLimit || uploadStore.uploadState.status === "loading"
                }
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

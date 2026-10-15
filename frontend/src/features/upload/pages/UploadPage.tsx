import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import React, { useEffect, useRef, useState } from "react";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Card, CardBody } from "@/shared/components/Card/Card";
import { Button } from "@/shared/components/Button/Button";

import { ReceiptLineCard } from "../components/ReceiptLineCard";
import { ExtractedStep } from "../components/ExtractedStep";

import { ResolveStep } from "../components/ResolveStep";
import { ReceiptQuotaNote } from "../components/ReceiptQuotaNote";
import { ManualExpenseDialog } from "@/features/receipts/components/ManualExpenseDialog";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

export const UploadPage = observer(function UploadPage() {
  const { uploadStore, quotaStore, tripsStore } = useStores();
  const { t } = useTranslation(["upload", "receipts"]);
  const [addingExpense, setAddingExpense] = useState(false);
  const [params] = useSearchParams();
  const tripId = params.get("trip");

  useEffect(() => {
    void quotaStore.load();
  }, [quotaStore]);

  // Receipts dated within a trip are asked about, and an upload begun on a trip's page
  // goes to that trip (F20.1); either needs the trips at hand.
  useEffect(() => {
    void tripsStore.load().then(() => {
      uploadStore.setFromTrip(tripsStore.trips.find((trip) => trip.id === tripId) ?? null);
    });
    return () => {
      uploadStore.setFromTrip(null);
    };
  }, [tripsStore, uploadStore, tripId]);
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

  if (
    uploadStore.currentStep === 2 &&
    uploadStore.uploadState.status === "success" &&
    uploadStore.extractedData
  ) {
    return <ExtractedStep />;
  }

  if (
    uploadStore.currentStep === 3 &&
    uploadStore.uploadState.status === "success" &&
    uploadStore.extractedData
  ) {
    return <ResolveStep />;
  }

  return (
    <Container size="narrow" gutter={false} className="py-4 md:py-9">
      <Stack className="gap-4 md:gap-6">
        {/* A phone's header already says "New receipt" (upload-mobile.html). */}
        <div className="hidden items-center md:flex">
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              1
            </span>
            <span className="text-[14px] font-semibold text-foreground">{t("steps.photos")}</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-border mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-border rounded-pill bg-background text-border-strong text-[13px] font-bold">
              2
            </span>
            <span className="text-[14px] font-semibold text-border-strong">{t("steps.read")}</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-border mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-border rounded-pill bg-background text-border-strong text-[13px] font-bold">
              3
            </span>
            <span className="text-[14px] font-semibold text-border-strong">
              {t("steps.resolve")}
            </span>
          </span>
        </div>

        <div>
          <h1 className="m-0 text-[22px] font-bold tracking-tight md:text-[30px]">
            {t("add.title")}
          </h1>
          <p className="m-0 text-[15px] text-muted-foreground mt-1">{t("add.formats")}</p>
          {/* F20.5: cash for a tour has nothing to photograph; it is typed in instead. */}
          <p className="m-0 mt-1 text-[15px] text-muted-foreground">
            {t("add.noReceipt")}{" "}
            <button
              type="button"
              className="inline-flex min-h-11 cursor-pointer items-center bg-transparent p-0 font-semibold text-primary underline-offset-2 hover:underline md:min-h-0"
              onClick={() => {
                setAddingExpense(true);
              }}
            >
              {t("receipts:manual.openLong")}
            </button>
          </p>
        </div>

        <ReceiptQuotaNote needed={uploadStore.lines.length} />

        <div
          className="flex w-full gap-1 border border-border rounded-control bg-muted p-1 md:inline-flex md:w-auto md:self-start"
          role="tablist"
        >
          <button
            className={`inline-flex flex-1 items-center justify-center gap-2 border-none rounded-[9px] px-4 py-[9px] text-sm cursor-pointer transition-colors md:flex-none ${
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
            {t("add.one")}
          </button>
          <button
            className={`inline-flex flex-1 items-center justify-center gap-2 border-none rounded-[9px] px-4 py-[9px] text-sm cursor-pointer transition-colors md:flex-none ${
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
            {t("add.several")}
            <span className="hidden md:inline">{t("add.severalWide")}</span>
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
                isLoading={uploadStore.isProcessing}
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
                {t("add.receipt")}
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

          {uploadStore.mode === "multiple" && !uploadStore.isProcessing && (
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
              {t("add.another")}
            </button>
          )}

          {uploadStore.uploadState.status === "error" && uploadStore.errorTitle && (
            <Card flush className="mt-4 border-tone-error-border">
              <div className="flex items-center justify-between bg-tone-error-bg border-b border-tone-error-border px-5 py-2">
                <span className="text-[11px] font-bold text-tone-error-text">
                  {uploadStore.errorTitle}
                </span>
                <span className="text-[11px] font-bold text-tone-error-text">ERR</span>
              </div>
              <CardBody>
                <div className="flex gap-2 text-tone-error-text bg-tone-error-bg p-3 rounded-md">
                  <svg
                    className="mt-0.5 shrink-0"
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
                    <span className="text-[13px] font-bold">{t("add.failed")}</span>
                    <span className="text-xs leading-relaxed">{uploadStore.errorDetails}</span>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}
        </Stack>

        {uploadStore.totalFilesCount > 0 && (
          <div className="flex flex-col gap-3 border-t border-border pt-5 md:flex-row md:items-center md:justify-between md:gap-4">
            <span className="text-[13px] text-muted-foreground">
              {t("add.receipts", { count: uploadStore.lines.length })} &middot;{" "}
              {t("add.photos", { count: uploadStore.totalFilesCount })} &middot;{" "}
              {t("add.size", { size: uploadStore.allLinesTotalSizeMB })}
            </span>
            <div className="flex flex-col-reverse gap-2 md:flex-row md:items-center md:gap-3">
              <Button
                variant="ghost"
                onClick={() => {
                  uploadStore.startOver();
                }}
              >
                {t("add.cancel")}
              </Button>
              <Button
                variant="primary"
                onClick={handleUploadClick}
                disabled={
                  uploadStore.isAnyLineOverLimit ||
                  uploadStore.uploadState.status === "loading" ||
                  !quotaStore.allows(uploadStore.lines.length)
                }
              >
                {uploadStore.uploadState.status === "loading"
                  ? uploadStore.totalItems > 0
                    ? t("add.processed", {
                        done: uploadStore.processedItems,
                        total: uploadStore.totalItems,
                      })
                    : t("add.sending")
                  : t("add.read")}
                {uploadStore.uploadState.status !== "loading" && (
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
                )}
              </Button>
            </div>
          </div>
        )}
      </Stack>
      {addingExpense && (
        <ManualExpenseDialog
          fromTrip={uploadStore.fromTrip ?? undefined}
          onClose={() => {
            setAddingExpense(false);
          }}
        />
      )}
    </Container>
  );
});

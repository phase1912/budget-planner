import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import React, { useRef, useState } from "react";

export const UploadPage = observer(function UploadPage() {
  const { uploadStore } = useStores();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFileName(file.name);
      await uploadStore.uploadFile(file);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="app-container app-container--narrow flex flex-col gap-6 py-9">
      <div className="stepper">
        <span className="step step--current">
          <span className="step__marker">1</span>
          <span className="step__label">Photos</span>
        </span>
        <span className="stepper__line"></span>
        <span className="step">
          <span className="step__marker">2</span>
          <span className="step__label">What we read</span>
        </span>
        <span className="stepper__line"></span>
        <span className="step">
          <span className="step__marker">3</span>
          <span className="step__label">Resolve</span>
        </span>
      </div>

      <div className="titles">
        <h1 className="page-title page-title--lg">Add the photos</h1>
        <p className="page-sub">
          JPEG, PNG, HEIC or a PDF scan. Up to 10 photos and 50&nbsp;MB per receipt.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <section className="card card--surface p-5">
          {uploadStore.uploadState.status === "loading" ? (
            <div className="flex items-center gap-3 mb-4">
              <span className="icon-tile icon-tile--warning">
                <svg
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
              </span>
              <span className="text-[13px] font-semibold">Uploading...</span>
            </div>
          ) : (
            <button
              className="dropzone dropzone--wide"
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
          )}
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={(e) => void handleFileChange(e)}
            accept="image/jpeg, image/png, image/heic, application/pdf"
          />
        </section>

        {uploadStore.uploadState.status === "success" && (
          <div className="card card--flush panel">
            <div className="panel__body">
              <div className="note note--success items-start w-full px-4 py-3.5">
                <div className="flex flex-col gap-1">
                  <span className="text-[13px] font-bold text-success">
                    File successfully added!
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {uploadStore.uploadState.status === "error" && uploadStore.errorTitle && (
          <div className="card card--flush panel">
            <div className="panel__label">
              <span className="panel__title">{uploadStore.errorTitle}</span>
              <span className="panel__ref">A2</span>
            </div>
            <div className="panel__body">
              <div className="note note--error items-start w-full px-4 py-3.5">
                <svg
                  className="note__icon mt-0.5 text-error"
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
                  <span className="text-[13px] font-bold text-error">
                    &ldquo;{selectedFileName}&rdquo; was not added
                  </span>
                  <span className="text-[12px] leading-relaxed">{uploadStore.errorDetails}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

import React, { useRef } from "react";
import { Card } from "@/shared/components/Card/Card";
import { Stack } from "@/shared/components/Layout/Layout";
import { FilePreview } from "./FilePreview";

interface ReceiptLineCardProps {
  index: number;
  files: File[];
  totalSizeMB: string;
  isOverLimit: boolean;
  isOverCount: boolean;
  isOverSize: boolean;
  onAddFiles: (files: File[]) => void;
  onRemoveFile: (fileIndex: number) => void;
  onRemoveLine?: () => void;
  showRemoveLine?: boolean;
}

export function ReceiptLineCard({
  index,
  files,
  totalSizeMB,
  isOverLimit,
  isOverCount,
  isOverSize,
  onAddFiles,
  onRemoveFile,
  onRemoveLine,
  showRemoveLine,
}: ReceiptLineCardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newFiles = Array.from(event.target.files ?? []);
    if (newFiles.length > 0) {
      onAddFiles(newFiles);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const sizePercentage = Math.min(100, (parseFloat(totalSizeMB) / 50) * 100);
  const countPercentage = Math.min(100, (files.length / 10) * 100);
  const fillPercentage = Math.max(sizePercentage, countPercentage);

  return (
    <Card variant="surface" className={`p-5 ${isOverLimit ? "border-tone-error-border" : ""}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <span
            className={`inline-flex items-center justify-center w-[26px] h-[26px] rounded-pill text-xs font-bold ${
              isOverLimit
                ? "bg-tone-error-bg text-tone-error-text"
                : "bg-tone-primary-bg text-tone-primary-text"
            }`}
          >
            {index + 1}
          </span>
          <span className="text-[15px] font-semibold">Receipt</span>
        </div>
        {showRemoveLine && onRemoveLine && (
          <button
            onClick={onRemoveLine}
            className="text-muted-foreground hover:text-foreground p-1 rounded-full hover:bg-muted transition-colors cursor-pointer"
            aria-label="Remove receipt line"
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
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="flex items-center gap-2.5 mb-4 flex-wrap">
        {files.map((file, i) => (
          <FilePreview
            key={i}
            file={file}
            index={i}
            onRemove={() => {
              onRemoveFile(i);
            }}
          />
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

      {isOverLimit && (
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
              ? `${String(files.length - 10)} photos were not added — a receipt takes at most 10.`
              : `The photos add up to ${totalSizeMB} MB, exceeding the 50 MB limit.`}
          </span>
        </div>
      )}

      <Stack className="gap-[5px]">
        <div className="flex items-baseline justify-between">
          <span
            className={`text-xs ${isOverCount ? "font-semibold text-error" : "text-muted-foreground"}`}
          >
            {files.length} of 10 photos
          </span>
          <span
            className={`text-xs ${isOverSize ? "font-semibold text-error" : "text-muted-foreground"}`}
          >
            {totalSizeMB} of 50&nbsp;MB
          </span>
        </div>
        <span className="block h-[4px] rounded-[2px] bg-border overflow-hidden">
          <span
            className={`block h-full rounded-[2px] ${isOverLimit ? "bg-error" : "bg-primary"}`}
            style={{ width: `${String(fillPercentage)}%` }}
          ></span>
        </span>
      </Stack>

      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        multiple
        onChange={handleFileChange}
        accept="image/jpeg, image/png, image/heic, application/pdf"
      />
    </Card>
  );
}

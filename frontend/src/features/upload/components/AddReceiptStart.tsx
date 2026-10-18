import { useRef, useState } from "react";
import { Banknote, Camera, Check, Copy, FileUp, Mail } from "lucide-react";
import { useTranslation } from "react-i18next";

const ACCEPT = "image/jpeg, image/png, image/heic, application/pdf";

/** Whether the device has a touch screen, where a camera is at hand (F23.6). */
function touchDevice(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(pointer: coarse)").matches;
}

interface AddReceiptStartProps {
  onFiles: (files: File[]) => void;
  /** The account's receipt forwarding address, to copy (F11.2). */
  forwardingAddress: string | null;
  /** A payslip or transfer confirmation picked, to be read as income (F23.11). */
  onIncomeFile: (file: File) => void;
  /** Whether such a document is being read now. */
  readingIncome: boolean;
}

/**
 * The ways a receipt comes in (F23.6): the phone's own camera where there is one — the
 * browser opens it, no app needed — photos or a PDF from the device, forwarding an
 * e-receipt by email, and on a desktop dropping files on the page. Money that came in
 * starts here too: a payslip or transfer confirmation, read into an entry to confirm.
 */
export function AddReceiptStart({
  onFiles,
  forwardingAddress,
  onIncomeFile,
  readingIncome,
}: AddReceiptStartProps) {
  const { t } = useTranslation("upload");
  const camera = useRef<HTMLInputElement>(null);
  const files = useRef<HTMLInputElement>(null);
  const income = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const take = (list: FileList | null) => {
    const picked = Array.from(list ?? []);
    if (picked.length > 0) onFiles(picked);
  };
  const tile =
    "flex min-h-24 w-full items-center gap-4 rounded-card p-4 text-left transition-transform active:scale-[0.99]";

  return (
    <div className="flex flex-col gap-3">
      {touchDevice() && (
        <button
          type="button"
          className={`${tile} bg-primary text-primary-foreground`}
          onClick={() => camera.current?.click()}
        >
          <Camera size={30} aria-hidden="true" />
          <span className="flex flex-col">
            <span className="text-xl font-bold">{t("start.camera")}</span>
            <span className="text-md opacity-90">{t("start.cameraHint")}</span>
          </span>
        </button>
      )}
      <input
        ref={camera}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
        onChange={(event) => {
          take(event.target.files);
          event.target.value = "";
        }}
      />

      <button
        type="button"
        className={`${tile} bg-surface md:min-h-40 md:flex-col md:justify-center md:border-2 md:border-dashed md:text-center md:shadow-none ${
          dragging ? "md:border-primary md:bg-tone-primary-bg" : "md:border-border-strong"
        }`}
        onClick={() => files.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => {
          setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          take(event.dataTransfer.files);
        }}
      >
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
          <FileUp size={24} aria-hidden="true" />
        </span>
        <span className="flex flex-col">
          <span className="text-lg font-bold">
            <span className="md:hidden">{t("start.files")}</span>
            <span className="hidden md:inline">{t("start.drop")}</span>
          </span>
          <span className="text-md text-muted-foreground">{t("start.filesHint")}</span>
        </span>
      </button>
      <input
        ref={files}
        type="file"
        multiple
        accept={ACCEPT}
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
        onChange={(event) => {
          take(event.target.files);
          event.target.value = "";
        }}
      />

      <button
        type="button"
        disabled={readingIncome}
        className={`${tile} min-h-20 bg-surface disabled:opacity-70`}
        onClick={() => income.current?.click()}
      >
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
          <Banknote size={24} aria-hidden="true" />
        </span>
        <span className="flex flex-col" aria-live="polite">
          <span className="text-lg font-bold">
            {readingIncome ? t("start.reading") : t("start.income")}
          </span>
          <span className="text-md text-muted-foreground">{t("start.incomeHint")}</span>
        </span>
      </button>
      <input
        ref={income}
        type="file"
        accept={ACCEPT}
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onIncomeFile(file);
          event.target.value = "";
        }}
      />

      {forwardingAddress && (
        <div className={`${tile} min-h-20 bg-surface`}>
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
            <Mail size={24} aria-hidden="true" />
          </span>
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="text-lg font-bold">{t("start.email")}</span>
            <span className="truncate text-md text-muted-foreground">{forwardingAddress}</span>
          </span>
          <button
            type="button"
            aria-label={t("start.copy")}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-control text-primary hover:bg-tone-primary-bg"
            onClick={() => {
              void navigator.clipboard.writeText(forwardingAddress).then(() => {
                setCopied(true);
              });
            }}
          >
            {copied ? (
              <Check size={20} aria-hidden="true" />
            ) : (
              <Copy size={20} aria-hidden="true" />
            )}
          </button>
        </div>
      )}
    </div>
  );
}

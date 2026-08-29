import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Button } from "@/shared/components/Button/Button";
import { SecureImage, Note, IconTile } from "@/shared/components";
import { Card, CardHeader, CardFooter } from "@/shared/components/Card/Card";

interface ExtractedLineItem {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
  confidence?: number;
}

interface ExtractedData {
  merchant_name?: string | null;
  merchant_name_confidence?: number;
  transaction_date?: string | null;
  transaction_date_confidence?: number;
  transaction_time?: string | null;
  transaction_time_confidence?: number;
  receipt_total?: string | null;
  receipt_total_confidence?: number;
  is_receipt_confidence?: number;
  currency?: string;
  items_sum_matches_total?: boolean | null;
  computed_total?: string | null;
  requires_manual_review?: boolean | null;
  line_items?: ExtractedLineItem[];
  file_ids?: string[];
}

interface ExtractedDataPayload {
  extractions?: ExtractedData[];
}

export const ExtractedStep = observer(function ExtractedStep() {
  const { uploadStore } = useStores();

  const handleBack = () => {
    uploadStore.resetError();
    uploadStore.resetData();
    uploadStore.uploadState.reset();
  };

  const payload = uploadStore.extractedData as unknown as ExtractedDataPayload | null;
  const extractions = payload?.extractions;

  if (!extractions || extractions.length === 0) return null;

  const hasLowConfidence = extractions.some(
    (data) =>
      data.items_sum_matches_total === false ||
      data.items_sum_matches_total === null ||
      (data.is_receipt_confidence ?? 100) < 50 ||
      (data.merchant_name_confidence ?? 100) < 80 ||
      (data.transaction_date_confidence ?? 100) < 80 ||
      (data.receipt_total_confidence ?? 100) < 80 ||
      (data.line_items?.some((item) => (item.confidence ?? 100) < 80) ?? false),
  );
  const totalItems = extractions.reduce((acc, data) => acc + (data.line_items?.length ?? 0), 0);

  return (
    <Container size="narrow" className="py-9 pb-8">
      <Stack className="gap-6">
        <div className="flex items-center">
          <button
            type="button"
            className="inline-flex items-center gap-2.5 appearance-none bg-transparent border-none p-0 text-left cursor-pointer hover:opacity-80 transition-opacity"
            onClick={handleBack}
          >
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <span className="text-[14px] font-semibold text-foreground">Photos</span>
          </button>
          <span className="grow h-[2px] rounded-[1px] bg-primary mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              2
            </span>
            <span className="text-[14px] font-semibold text-foreground">What we read</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-border mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-[28px] h-[28px] border border-border rounded-pill bg-background text-border-strong text-[13px] font-bold">
              3
            </span>
            <span className="text-[14px] font-semibold text-border-strong">Resolve</span>
          </span>
        </div>

        <div className="flex flex-col gap-1">
          <h1 className="m-0 text-[30px] font-bold tracking-tight">What we read</h1>
          <p className="m-0 text-[15px] text-muted-foreground mt-1">
            {uploadStore.lines.length} receipt{uploadStore.lines.length === 1 ? "" : "s"},{" "}
            {totalItems} items, from {uploadStore.totalFilesCount} photos. Nothing is stored yet.
          </p>
        </div>

        {hasLowConfidence && (
          <Note tone="warning">
            Some things need a decision from you — you will get to them on the next step. Read
            through first and fix anything obviously wrong here.
          </Note>
        )}

        {extractions.map((data, index) => {
          const merchantName = data.merchant_name ?? "Unknown merchant";
          const merchantNameLowConf = (data.merchant_name_confidence ?? 100) < 80;
          const transactionDate = data.transaction_date ?? "Unknown date";
          const transactionDateLowConf = (data.transaction_date_confidence ?? 100) < 80;
          const receiptTotalLowConf = (data.receipt_total_confidence ?? 100) < 80;
          const isNotReceipt = (data.is_receipt_confidence ?? 100) < 50;
          const matchesTotal = data.items_sum_matches_total;
          const lineItems = data.line_items ?? [];
          const fileIds = data.file_ids ?? [];

          return (
            <Card
              key={index}
              flush
              className={matchesTotal === false ? "border-tone-error-border mt-4" : "mt-4"}
            >
              <CardHeader className="flex items-center justify-between">
                <div className="flex items-center gap-3.5">
                  <div className="flex gap-1.5">
                    {fileIds.slice(0, 2).map((id) => (
                      <SecureImage
                        key={id}
                        fileId={id}
                        alt="receipt thumb"
                        className="w-9 h-11 object-cover rounded-md"
                      />
                    ))}
                    {fileIds.length > 2 && (
                      <span className="inline-flex items-center justify-center w-9 h-11 rounded-md bg-muted text-[11px] font-bold text-muted-foreground">
                        +{fileIds.length - 2}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span
                      className={`text-base font-bold ${merchantNameLowConf ? "text-tone-warning-text" : ""}`}
                    >
                      {merchantName}
                    </span>
                    <span
                      className={`text-[13px] ${transactionDateLowConf ? "text-tone-warning-text" : "text-muted-foreground"}`}
                    >
                      {transactionDate} &middot; {fileIds.length} photo
                      {fileIds.length === 1 ? "" : "s"}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3.5">
                  <div className="flex flex-col items-end gap-0.5">
                    {matchesTotal === null && (
                      <span className="text-[11px] font-semibold text-tone-warning-text">
                        Total &middot; unsure
                      </span>
                    )}
                    {matchesTotal === false && (
                      <span className="text-[11px] font-semibold text-tone-error-text">
                        Total &middot; not found
                      </span>
                    )}
                    <span
                      className={`text-lg font-bold tabular-nums ${receiptTotalLowConf ? "text-tone-warning-text" : ""}`}
                    >
                      {data.receipt_total
                        ? `${data.receipt_total} ${data.currency ?? ""}`.trim()
                        : "—"}
                    </span>
                  </div>
                  <button
                    className="inline-flex items-center justify-center w-8 h-8 rounded-md border border-border text-muted-foreground hover:bg-muted transition-colors ml-1"
                    aria-label="Edit this receipt"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
                    </svg>
                  </button>
                </div>
              </CardHeader>

              {isNotReceipt && (
                <Note
                  tone="error"
                  className="rounded-none border-x-0 border-t-0 px-5 py-3.5 items-start"
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="font-bold">This doesn't look like a receipt</span>
                    <span className="opacity-90">
                      Please review carefully. You can proceed to resolve it manually or go back to
                      upload a different photo.
                    </span>
                  </div>
                </Note>
              )}
              {data.requires_manual_review && (
                <div className="flex flex-col gap-3 px-5 py-4 border-b border-border bg-card">
                  <div className="flex items-start gap-3">
                    <IconTile tone="error">
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
                        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
                        <path d="M12 9v4" />
                        <path d="M12 17h.01" />
                      </svg>
                    </IconTile>
                    <div className="flex flex-col gap-1">
                      <span className="text-[13px] font-bold text-foreground">
                        {merchantName || "Receipt"} needs you
                      </span>
                      <span className="text-[12px] leading-relaxed text-muted-foreground prose">
                        No total or date could be read, so it is excluded from budget calculation
                        until you fill it in. The month says so on its face.
                      </span>
                    </div>
                  </div>
                  <Button variant="danger-solid" size="sm" className="self-start text-[12px]">
                    Enter the total
                  </Button>
                </div>
              )}

              <div className="grid grid-cols-[minmax(0,1fr)_48px_84px_92px_148px] items-center gap-3 px-5 py-2.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <span>Item</span>
                <span className="text-right">Qty</span>
                <span className="text-right">Unit</span>
                <span className="text-right">Total</span>
                <span>Category</span>
              </div>

              {lineItems.map((item, idx) => {
                const itemLowConf = (item.confidence ?? 100) < 80;
                return (
                  <div
                    key={idx}
                    className="grid grid-cols-[minmax(0,1fr)_48px_84px_92px_148px] items-center gap-3 px-5 py-3 border-b border-border last:border-b-0 hover:bg-muted/50 transition-colors text-[13px]"
                  >
                    <span
                      className={`font-medium truncate ${itemLowConf ? "text-tone-warning-text" : "text-foreground"}`}
                    >
                      {item.name}
                    </span>
                    <span
                      className={`text-right tabular-nums ${itemLowConf ? "text-tone-warning-text" : "text-muted-foreground"}`}
                    >
                      {item.quantity}
                    </span>
                    <span
                      className={`text-right tabular-nums ${itemLowConf ? "text-tone-warning-text" : "text-muted-foreground"}`}
                    >
                      {item.unit_price}
                    </span>
                    <span
                      className={`text-right font-semibold tabular-nums ${itemLowConf ? "text-tone-warning-text" : "text-foreground"}`}
                    >
                      {item.total_price}
                    </span>
                    <span>
                      <span className="inline-flex items-center justify-center h-[22px] px-2 rounded-full bg-muted text-muted-foreground text-[11px] font-bold">
                        Uncategorized
                      </span>
                    </span>
                  </div>
                );
              })}

              <CardFooter
                className={
                  matchesTotal === false
                    ? "bg-tone-error-bg border-t border-tone-error-border"
                    : "border-t border-border"
                }
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-[13px] text-muted-foreground tabular-nums">
                    {lineItems.length} items &middot; lines add up to{" "}
                    {data.computed_total ?? "0.00"}
                  </span>
                  {matchesTotal === true && (
                    <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-primary">
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                      Matches the printed total
                    </span>
                  )}
                  {matchesTotal === false && (
                    <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-tone-error-text">
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
                        <path d="M12 9v4" />
                        <path d="M12 17h.01" />
                      </svg>
                      {!data.receipt_total
                        ? "Nothing to check them against"
                        : "Lines do not match printed total"}
                    </span>
                  )}
                </div>
              </CardFooter>
            </Card>
          );
        })}

        <div className="flex items-center justify-between gap-4 mt-4">
          <Button variant="ghost" onClick={handleBack}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-2"
            >
              <path d="m15 18-6-6 6-6" />
            </svg>
            Back to photos
          </Button>
          <Button variant="primary">
            Resolve {totalItems} things
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="ml-2"
            >
              <path d="M5 12h14" />
              <path d="m12 5 7 7-7 7" />
            </svg>
          </Button>
        </div>
      </Stack>
    </Container>
  );
});

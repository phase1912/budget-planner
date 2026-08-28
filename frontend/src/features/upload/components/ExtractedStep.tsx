import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { Container, Stack } from "@/shared/components/Layout/Layout";
import { Button } from "@/shared/components/Button/Button";
import { SecureImage } from "@/shared/components";
import { Card, CardHeader, CardFooter } from "@/shared/components/Card/Card";

interface ExtractedLineItem {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

interface ExtractedData {
  merchant_name?: string | null;
  transaction_date?: string | null;
  receipt_total?: string | null;
  currency?: string;
  items_sum_matches_total?: boolean | null;
  computed_total?: string | null;
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

  const hasAnyWarning = extractions.some(
    (data) => data.items_sum_matches_total === false || data.items_sum_matches_total === null,
  );
  const totalItems = extractions.reduce((acc, data) => acc + (data.line_items?.length ?? 0), 0);

  return (
    <Container size="narrow" className="pb-8">
      <Stack className="gap-6">
        <div className="flex flex-col gap-1">
          <h2 className="m-0 text-[32px] font-bold text-foreground">What we read</h2>
          <p className="m-0 text-[15px] text-muted-foreground mt-1">
            {uploadStore.lines.length} receipt{uploadStore.lines.length === 1 ? "" : "s"},{" "}
            {totalItems} items, from {uploadStore.totalFilesCount} photos. Nothing is stored yet.
          </p>
        </div>

        {hasAnyWarning && (
          <div className="note note--warning">
            <svg
              className="note__icon"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--tone-warning-text)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4" />
              <path d="M12 16h.01" />
            </svg>
            <span className="note__text">
              Some things need a decision from you — you will get to them on the next step. Read
              through first and fix anything obviously wrong here.
            </span>
          </div>
        )}

        {extractions.map((data, index) => {
          const merchantName = data.merchant_name ?? "Unknown merchant";
          const transactionDate = data.transaction_date ?? "Unknown date";
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
                    <span className="text-base font-bold">{merchantName}</span>
                    <span className="text-muted-foreground text-[13px]">
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
                    <span className="text-lg font-bold tabular-nums">
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

              <div className="grid grid-cols-[minmax(0,1fr)_48px_84px_92px_148px] items-center gap-3 px-5 py-2.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <span>Item</span>
                <span className="text-right">Qty</span>
                <span className="text-right">Unit</span>
                <span className="text-right">Total</span>
                <span>Category</span>
              </div>

              {lineItems.map((item, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-[minmax(0,1fr)_48px_84px_92px_148px] items-center gap-3 px-5 py-3 border-b border-border last:border-b-0 hover:bg-muted/50 transition-colors text-[13px]"
                >
                  <span className="font-medium text-foreground truncate">{item.name}</span>
                  <span className="text-right text-muted-foreground tabular-nums">
                    {item.quantity}
                  </span>
                  <span className="text-right text-muted-foreground tabular-nums">
                    {item.unit_price}
                  </span>
                  <span className="text-right font-semibold text-foreground tabular-nums">
                    {item.total_price}
                  </span>
                  <span>
                    <span className="inline-flex items-center justify-center h-[22px] px-2 rounded-full bg-muted text-muted-foreground text-[11px] font-bold">
                      Uncategorized
                    </span>
                  </span>
                </div>
              ))}

              <CardFooter
                className={
                  matchesTotal === false
                    ? "bg-tone-error-bg border-t border-tone-error-border"
                    : "border-t border-border"
                }
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-[13px] text-muted-foreground tabular-nums">
                    {lineItems.length} items &middot; lines add up to {data.computed_total ?? "0.00"}
                  </span>
                  {matchesTotal === true && (
                    <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-tone-success-text">
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

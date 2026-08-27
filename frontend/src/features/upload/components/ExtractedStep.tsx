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
  line_items?: ExtractedLineItem[];
}

export const ExtractedStep = observer(function ExtractedStep() {
  const { uploadStore } = useStores();

  const handleBack = () => {
    uploadStore.resetError();
    uploadStore.extractedData = null;
    uploadStore.uploadState.reset();
  };

  // The parsed result from the LLM
  const data = uploadStore.extractedData as unknown as ExtractedData | null;
  if (!data) return null;

  // We only support displaying 1 receipt right now in the UI even if they uploaded multiple.
  // The backend currently parses them as a single ExtractionResult.

  const lineItems: ExtractedLineItem[] = data.line_items ?? [];
  const matchesTotal = data.items_sum_matches_total ?? null;
  const merchantName = data.merchant_name ?? "Unknown Merchant";
  const transactionDate = data.transaction_date ?? "Unknown Date";

  return (
    <Container size="narrow" className="py-9">
      <Stack className="gap-6">
        <div className="flex items-center">
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-7 h-7 border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
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
            <span className="text-sm font-semibold text-foreground">Photos</span>
          </span>
          <span className="grow h-[2px] rounded-[1px] bg-primary mx-4"></span>
          <span className="inline-flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center w-7 h-7 border border-transparent rounded-pill bg-primary text-primary-foreground text-[13px] font-bold">
              2
            </span>
            <span className="text-sm font-semibold text-foreground">What we read</span>
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
          <h1 className="m-0 text-[30px] font-bold tracking-tight">What we read</h1>
          <p className="m-0 text-[15px] text-muted-foreground mt-1">
            {uploadStore.lines.length} receipt, {lineItems.length} items, from{" "}
            {uploadStore.totalFilesCount} photos. Nothing is stored yet.
          </p>
        </div>

        {(matchesTotal === false || matchesTotal === null) && (
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

        <Card flush className={matchesTotal === false ? "border-error" : ""}>
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="flex gap-1.5">
                {uploadStore.fileIds.slice(0, 2).map((id) => (
                  <SecureImage
                    key={id}
                    fileId={id}
                    alt="receipt thumb"
                    className="w-9 h-11 object-cover rounded-md"
                  />
                ))}
                {uploadStore.fileIds.length > 2 && (
                  <span className="inline-flex items-center justify-center w-9 h-11 rounded-md bg-muted text-[11px] font-bold text-muted-foreground">
                    +{uploadStore.fileIds.length - 2}
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-base font-bold">{merchantName}</span>
                <span className="text-muted-foreground text-[13px]">
                  {transactionDate} &middot; {uploadStore.fileIds.length} photo
                  {uploadStore.fileIds.length === 1 ? "" : "s"}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3.5">
              <div className="flex flex-col items-end gap-0.5">
                {matchesTotal === null && (
                  <span className="text-[11px] font-semibold text-warning-text">
                    Total &middot; unsure
                  </span>
                )}
                {matchesTotal === false && (
                  <span className="text-[11px] font-semibold text-error">
                    Total &middot; not found
                  </span>
                )}
                <span className="text-lg font-bold">
                  {data.receipt_total ? `${data.receipt_total} ${data.currency ?? ""}`.trim() : "—"}
                </span>
              </div>
            </div>
          </CardHeader>

          <div className="grid grid-cols-[minmax(0,1fr)_48px_84px_92px] items-center gap-3 px-5 py-2.5 text-xs font-semibold text-muted-foreground border-b border-border">
            <span>Item</span>
            <span className="text-right">Qty</span>
            <span className="text-right">Unit</span>
            <span className="text-right">Total</span>
          </div>

          {lineItems.map((item, idx) => (
            <div
              key={idx}
              className="grid grid-cols-[minmax(0,1fr)_48px_84px_92px] items-center gap-3 px-5 py-3 border-b border-border last:border-b-0 hover:bg-muted/50 transition-colors"
            >
              <span className="font-medium text-foreground truncate">{item.name}</span>
              <span className="text-right text-muted-foreground">{item.quantity}</span>
              <span className="text-right text-muted-foreground">{item.unit_price}</span>
              <span className="text-right font-semibold text-foreground">{item.total_price}</span>
            </div>
          ))}

          <CardFooter className={matchesTotal === false ? "bg-error-bg" : ""}>
            <div className="flex items-center justify-between w-full">
              <span className="text-[13px] text-muted-foreground">{lineItems.length} items</span>
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
                <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-error">
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
                  Lines do not match printed total
                </span>
              )}
            </div>
          </CardFooter>
        </Card>

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
            Resolve {lineItems.length} things
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

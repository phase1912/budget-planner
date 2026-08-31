import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { ReceiptDetailModal } from "../components/ReceiptDetailModal";
import { Card, Button, Input, IconTile } from "@/shared/components";

export const ReceiptsPage = observer(() => {
  const { receiptStore } = useStores();

  useEffect(() => {
    void receiptStore.fetchReceipts(receiptStore.page, receiptStore.size);
  }, [receiptStore]);

  return (
    <div className="flex-grow flex flex-col items-center py-10 px-8">
      <div className="w-full max-w-[960px] flex flex-col gap-7">
        <div className="flex items-end justify-between gap-6">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[28px] font-bold tracking-[-0.02em] text-foreground">
              Receipts
            </h1>
            <p className="m-0 text-[15px] text-muted-foreground tabular-nums">
              {String(receiptStore.total)} stored &middot; newest first
            </p>
          </div>
          <a
            href="/statistics"
            className="inline-flex items-center gap-[7px] text-[14px] font-semibold text-primary hover:text-primary-hover"
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
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export this list
          </a>
        </div>

        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-[10px]">
            {/* Mock filters for now */}
            <Button variant="secondary" size="sm">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-muted-foreground"
              >
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <path d="M16 2v4" />
                <path d="M8 2v4" />
                <path d="M3 10h18" />
              </svg>
              All dates
            </Button>
            <Button variant="secondary" size="sm">
              Any status
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-muted-foreground"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </Button>
          </div>
          <div className="relative w-[250px]">
            <svg
              className="absolute left-3 top-[11px] text-muted-foreground pointer-events-none"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <Input
              className="pl-9 py-[9px] text-[13px]"
              type="search"
              placeholder="Merchant or item"
              aria-label="Search receipts"
            />
          </div>
        </div>

        <Card flush>
          <div className="grid grid-cols-[minmax(0,1fr)_120px_92px_120px_170px_28px] items-center gap-4 px-[18px] py-[12px] bg-surface border-b border-border">
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
              Merchant
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
              Date
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
              Items
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
              Total
            </span>
            <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
              Status
            </span>
            <span></span>
          </div>

          {receiptStore.isLoadingList ? (
            <div className="p-[18px] text-center text-muted-foreground">Loading...</div>
          ) : receiptStore.receipts.length === 0 ? (
            <div className="p-[18px] text-center text-muted-foreground">No receipts found.</div>
          ) : (
            receiptStore.receipts.map((receipt) => {
              const isParsed = receipt.status === "parsed";
              const isFailed = receipt.status === "failed";
              const isReview = receipt.status === "manual_review";

              let rowBg = "hover:bg-surface";
              if (isFailed) rowBg = "bg-tone-error-bg";
              else if (isReview) rowBg = "bg-tone-warning-bg";

              return (
                <button
                  key={receipt.id}
                  className={`grid grid-cols-[minmax(0,1fr)_120px_92px_120px_170px_28px] items-center gap-4 px-[18px] py-[14px] w-full text-left border-b border-border last:border-0 cursor-pointer transition-colors ${rowBg}`}
                  onClick={() => {
                    void receiptStore.fetchReceiptDetail(receipt.id);
                  }}
                >
                  <span className="flex items-center gap-[11px] text-[14px] font-semibold text-foreground">
                    <IconTile
                      tone={
                        isParsed ? "success" : isFailed ? "error" : isReview ? "warning" : "default"
                      }
                      size="sm"
                    >
                      {isFailed ? (
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
                          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
                          <path d="M12 9v4" />
                          <path d="M12 17h.01" />
                        </svg>
                      ) : (
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
                          <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
                          <path d="M16 8H8" />
                          <path d="M16 12H8" />
                        </svg>
                      )}
                    </IconTile>
                    {receipt.merchant_name ?? "Unknown Merchant"}
                  </span>
                  <span className="tabular-nums text-muted-foreground text-[13px]">
                    {receipt.transaction_date
                      ? new Intl.DateTimeFormat("en-GB", {
                          day: "numeric",
                          month: "short",
                        }).format(new Date(receipt.transaction_date)) +
                        ", " +
                        new Intl.DateTimeFormat("en-GB", {
                          hour: "2-digit",
                          minute: "2-digit",
                        }).format(new Date(receipt.transaction_date))
                      : "Unknown"}
                  </span>
                  <span className="tabular-nums text-muted-foreground text-right text-[13px]">
                    {receipt.line_items.length}
                  </span>
                  <span className="tabular-nums text-right text-[14px] font-semibold text-foreground">
                    {receipt.total_amount ? Number(receipt.total_amount).toFixed(2) : "—"}
                  </span>
                  <span>
                    <span
                      className={`inline-flex items-center gap-[6px] rounded-full px-[11px] py-[5px] text-[12px] font-semibold whitespace-nowrap ${
                        isParsed
                          ? "bg-tone-primary-bg text-tone-primary-text"
                          : isFailed
                            ? "bg-tone-error-bg text-tone-error-text"
                            : isReview
                              ? "bg-tone-warning-bg text-tone-warning-text"
                              : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {isParsed && (
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      )}
                      {isFailed && (
                        <svg
                          width="13"
                          height="13"
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
                      )}
                      {isReview && (
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <circle cx="12" cy="12" r="10" />
                          <path d="M12 8v4" />
                          <path d="M12 16h.01" />
                        </svg>
                      )}
                      {isParsed
                        ? "In the total"
                        : isFailed
                          ? "Out of the total"
                          : isReview
                            ? "Needs review"
                            : receipt.status}
                    </span>
                  </span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="text-muted-foreground"
                  >
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                </button>
              );
            })
          )}
        </Card>

        <div className="flex items-center justify-between gap-4 mt-4">
          <span className="tabular-nums text-muted-foreground text-[13px]">
            {receiptStore.total > 0
              ? `${String((receiptStore.page - 1) * receiptStore.size + 1)}–${String(
                  Math.min(receiptStore.page * receiptStore.size, receiptStore.total),
                )} of ${String(receiptStore.total)}`
              : "0 of 0"}
          </span>
          <div className="flex items-center gap-[6px]">
            <button
              className="inline-flex items-center justify-center min-w-[36px] h-[36px] border border-border rounded-chip bg-background text-foreground px-[10px] text-[13px] font-semibold cursor-pointer disabled:text-border-strong disabled:cursor-default"
              aria-label="Previous page"
              disabled={receiptStore.page <= 1}
              onClick={() => {
                void receiptStore.fetchReceipts(receiptStore.page - 1, receiptStore.size);
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
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
            <span className="inline-flex items-center justify-center min-w-[36px] h-[36px] border border-primary rounded-chip bg-primary text-primary-foreground px-[10px] text-[13px] font-semibold">
              {receiptStore.page}
            </span>
            <button
              className="inline-flex items-center justify-center min-w-[36px] h-[36px] border border-border rounded-chip bg-background text-foreground px-[10px] text-[13px] font-semibold cursor-pointer disabled:text-border-strong disabled:cursor-default"
              aria-label="Next page"
              disabled={receiptStore.page >= receiptStore.pages}
              onClick={() => {
                void receiptStore.fetchReceipts(receiptStore.page + 1, receiptStore.size);
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
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </div>
        </div>

        {receiptStore.selectedReceiptId && <ReceiptDetailModal />}
      </div>
    </div>
  );
});

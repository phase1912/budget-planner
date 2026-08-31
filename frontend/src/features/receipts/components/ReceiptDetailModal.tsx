import { observer } from "mobx-react-lite";
import { useStores } from "@/stores/StoreContext";
import { Modal, ModalHeader, ModalBody, ModalFooter, Button, IconTile } from "@/shared/components";

export const ReceiptDetailModal = observer(() => {
  const { receiptStore } = useStores();
  const receipt = receiptStore.receiptDetail;

  const handleClose = () => {
    receiptStore.clearSelection();
  };

  if (receiptStore.isLoadingDetail) {
    return (
      <Modal isOpen={true} onClose={handleClose} className="w-[660px]">
        <div className="p-6 text-center text-muted-foreground">Loading...</div>
      </Modal>
    );
  }

  if (!receipt) {
    return null;
  }

  return (
    <Modal isOpen={true} onClose={handleClose} className="w-[660px]">
      <ModalHeader>
        <div className="flex items-center gap-[13px]">
          <IconTile tone="success" size="lg">
            <svg
              width="20"
              height="20"
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
              <path d="M13 16H8" />
            </svg>
          </IconTile>
          <div className="flex flex-col gap-[3px]">
            <h2 className="m-0 text-[19px] font-bold">
              {receipt.merchant_name ?? "Unknown Merchant"}
            </h2>
            <span className="tabular-nums text-[13px] text-muted-foreground">
              {receipt.transaction_date
                ? new Intl.DateTimeFormat("en-GB", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  }).format(new Date(receipt.transaction_date)) +
                  " · " +
                  new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" }).format(
                    new Date(receipt.transaction_date),
                  )
                : "Unknown Date"}
              {" · "}
              {receipt.file_ids.length} photos
            </span>
          </div>
        </div>
        <button
          className="inline-flex items-center justify-center w-[34px] h-[34px] rounded-chip text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
          onClick={handleClose}
          aria-label="Close"
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
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </ModalHeader>

      <ModalBody>
        <div className="grid grid-cols-[minmax(0,1fr)_44px_78px_86px_132px] items-center gap-[12px] pb-1 border-b border-border">
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
            Item
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
            Qty
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
            Unit
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-right">
            Total
          </span>
          <span className="text-[11px] font-semibold tracking-[0.05em] uppercase text-muted-foreground text-left">
            Category
          </span>
        </div>

        {receipt.line_items.map((item) => (
          <div
            key={item.id}
            className="grid grid-cols-[minmax(0,1fr)_44px_78px_86px_132px] items-center gap-[12px] py-[11px] border-b border-border min-h-[44px] last:border-0"
          >
            <span className="text-[13px] font-medium">{item.name}</span>
            <span className="tabular-nums text-muted-foreground text-right text-[13px]">
              {Number(item.quantity).toFixed(0)}
            </span>
            <span className="tabular-nums text-muted-foreground text-right text-[13px]">
              {Number(item.unit_price).toFixed(2)}
            </span>
            <span className="tabular-nums text-right text-[14px] font-semibold">
              {Number(item.total_price).toFixed(2)}
            </span>
            <span>
              <span
                className={`inline-flex items-center rounded-full px-[10px] py-[4px] text-[12px] font-semibold whitespace-nowrap ${
                  item.category?.name
                    ? "bg-tone-primary-bg text-tone-primary-text"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {item.category?.name ?? "Uncategorized"}
              </span>
            </span>
          </div>
        ))}
      </ModalBody>

      <ModalFooter>
        <div className="flex items-baseline gap-[10px]">
          <span className="text-[13px] font-medium text-muted-foreground">Total</span>
          <span className="tabular-nums text-[22px] font-bold tracking-[-0.02em] text-foreground">
            {receipt.total_amount ? Number(receipt.total_amount).toFixed(2) : "—"}
          </span>
        </div>
        <div className="flex items-center gap-[10px]">
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
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="9" cy="9" r="2" />
              <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
            </svg>
            Original photos
          </Button>
          <Button variant="primary" size="sm">
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
            Edit
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
});

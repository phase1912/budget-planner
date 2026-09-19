import { observer } from "mobx-react-lite";
import { Button, IconTile, Modal, ModalBody } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Confirms erasing a receipt, naming exactly what is about to be lost.
 *
 * Deletion is permanent and takes the photos with it, so the prose states the
 * merchant, the total, the item count and the photo count rather than asking
 * "are you sure?" about an unnamed thing.
 */
export const DeleteReceiptDialog = observer(function DeleteReceiptDialog() {
  const { receiptStore } = useStores();
  const receipt = receiptStore.receiptDetail;
  const isOpen = receiptStore.pendingDeleteId !== null;

  if (!isOpen || !receipt) return null;

  const itemCount = receipt.line_items.length;
  const photoCount = receipt.file_ids.length;
  const total = receipt.total_amount ? Number(receipt.total_amount).toFixed(2) : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        receiptStore.cancelDelete();
      }}
      className="w-full max-w-[460px]"
      aria-labelledby="delete-receipt-title"
    >
      <ModalBody className="flex flex-col gap-[18px]">
        <div className="flex items-start gap-3.5">
          <IconTile tone="error" size="lg">
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
              <path d="M3 6h18" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
              <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </IconTile>
          <div className="flex flex-col gap-[5px]">
            <h2 id="delete-receipt-title" className="text-[17px] font-bold tracking-[-0.01em]">
              Delete {receipt.merchant_name ? `“${receipt.merchant_name}”` : "this receipt"}?
            </h2>
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              {itemCount} item{itemCount === 1 ? "" : "s"}
              {total ? ` worth ${total}` : ""} and {photoCount}{" "}
              photo{photoCount === 1 ? "" : "s"} will be erased. This cannot be undone.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-[10px]">
          <Button
            variant="ghost"
            onClick={() => {
              receiptStore.cancelDelete();
            }}
          >
            Keep it
          </Button>
          <Button
            variant="danger-solid"
            disabled={receiptStore.isDeleting}
            onClick={() => {
              void receiptStore.deleteReceipt(receipt.id);
            }}
          >
            {receiptStore.isDeleting ? "Deleting…" : "Delete receipt"}
          </Button>
        </div>
      </ModalBody>
    </Modal>
  );
});
